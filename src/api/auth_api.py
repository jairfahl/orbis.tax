"""
src/api/auth_api.py — Dependencies de autenticação da FastAPI.

verificar_token_api : valida X-API-Key interno (todos os endpoints protegidos)
verificar_sessao    : valida X-API-Key + session_id do JWT (usado em /v1/auth/me)
                      — garante sessão única: novo login invalida sessão anterior.
"""

import os
from typing import Optional

from fastapi import Header, HTTPException

from auth import decodificar_token
from src.db.pool import get_conn, put_conn


def verificar_token_api(x_api_key: str = Header(...)):
    """
    FastAPI dependency: valida o header X-API-Key.

    Levanta 401 se a chave estiver ausente ou incorreta.
    Levanta RuntimeError (500) se API_INTERNAL_KEY não estiver configurada no ambiente.
    """
    api_key = os.getenv("API_INTERNAL_KEY")
    if not api_key:
        raise RuntimeError("API_INTERNAL_KEY não configurada no ambiente.")
    if x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Não autorizado.")


def verificar_sessao(
    authorization: Optional[str] = Header(None),
    x_api_key: str = Header(...),
):
    """
    FastAPI dependency: valida X-API-Key + session_id do JWT.

    Usado em /v1/auth/me para garantir sessão única por usuário.
    Se um segundo login ocorrer, o session_id do banco muda e o JWT antigo
    retorna 401 com detail='session_expired' na próxima chamada a este endpoint.

    Tolerância de transição: JWTs sem session_id (emitidos antes da migration)
    são aceitos sem validação de sessão.
    """
    # 1. Validar X-API-Key (mesmo comportamento de verificar_token_api)
    api_key = os.getenv("API_INTERNAL_KEY")
    if not api_key:
        raise RuntimeError("API_INTERNAL_KEY não configurada no ambiente.")
    if x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Não autorizado.")

    # 2. Se não há JWT no header Authorization, tolerar (best-effort)
    if not authorization or not authorization.startswith("Bearer "):
        return

    # 3. Decodificar JWT
    token = authorization.split(" ", 1)[1]
    payload = decodificar_token(token)
    if not payload or not payload.get("session_id"):
        return  # JWT antigo sem session_id — tolerar na transição

    # 4. Comparar session_id do JWT com o session_id atual no banco
    user_id = payload.get("sub")
    jwt_session_id = payload.get("session_id")

    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_id FROM users WHERE id = %s LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
        if row and str(row[0]) != jwt_session_id:
            raise HTTPException(status_code=401, detail="session_expired")
    finally:
        if conn:
            put_conn(conn)
