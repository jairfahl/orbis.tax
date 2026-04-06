"""
Módulo de metering MAU (Monthly Active Users).
Definição: usuário ativo = qualquer login no mês calendário.
"""

import logging
from datetime import date
from typing import Optional
import psycopg2

logger = logging.getLogger(__name__)


def registrar_mau(conn, user_id: str, tenant_id: str) -> None:
    """
    Registra um usuário ativo no mês corrente.
    Idempotente: múltiplos logins no mesmo mês geram um único registro.

    Args:
        conn: conexão ativa com o PostgreSQL
        user_id: UUID do usuário que acabou de fazer login
        tenant_id: UUID do tenant do usuário
    """
    if not user_id or not tenant_id:
        logger.warning("registrar_mau: user_id ou tenant_id ausente. Ignorando.")
        return

    # Primeiro dia do mês corrente
    hoje = date.today()
    active_month = hoje.replace(day=1)

    sql = """
        INSERT INTO mau_records (user_id, tenant_id, active_month)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, tenant_id, active_month) DO NOTHING;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, tenant_id, active_month))
        conn.commit()
        logger.info(
            "MAU registrado: user=%s tenant=%s month=%s",
            user_id, tenant_id, active_month
        )
    except Exception as e:
        logger.error("Falha ao registrar MAU: %s", e)
        conn.rollback()
        # Não propaga exceção — falha de metering não deve bloquear o login
