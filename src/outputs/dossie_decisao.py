"""
src/outputs/dossie_decisao.py — Gerador de Dossiê de Decisão (C4 / G13).

Wrapper sobre OutputEngine.gerar_dossie() que acrescenta semântica
de Legal Hold e imutabilidade conforme DC v7, Classe Documental 4.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import psycopg2

from src.outputs.engine import OutputEngine, OutputResult
from src.outputs.taxonomia import CLASSES_CONFIG, OutputClass

logger = logging.getLogger(__name__)


def _get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _marcar_legal_hold(output_id: int) -> None:
    """Marca o output como legal_hold=TRUE e imutavel=TRUE no banco."""
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE outputs
                    SET legal_hold = TRUE, imutavel = TRUE
                    WHERE id = %s
                    """,
                    (output_id,),
                )
    finally:
        conn.close()


def gerar_dossie_automatico(
    case_id: int,
    engine: Optional[OutputEngine] = None,
) -> Optional[OutputResult]:
    """
    Gera Dossiê de Decisão automaticamente ao concluir o P5.

    Cria o output via OutputEngine e aplica Legal Hold imediato.
    Idempotente: se um dossiê já existe para o case_id, retorna None sem duplicar.

    Args:
        case_id: ID do caso com P5 concluído
        engine: instância do OutputEngine (cria uma se None)

    Returns:
        OutputResult do dossiê gerado, ou None se já existia.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM outputs
                WHERE case_id = %s AND classe = 'dossie_decisao'
                LIMIT 1
                """,
                (case_id,),
            )
            if cur.fetchone():
                logger.info("Dossiê já existe para case_id=%d — ignorando duplicação", case_id)
                return None
    finally:
        conn.close()

    if engine is None:
        engine = OutputEngine()

    resultado = engine.gerar_dossie(case_id)
    _marcar_legal_hold(resultado.id)

    config = CLASSES_CONFIG[OutputClass.DOSSIE_DECISAO]
    logger.info(
        "Dossiê #%d gerado para case_id=%d — %s | legal_hold=%s | imutavel=%s",
        resultado.id,
        case_id,
        config["label"],
        config["legal_hold"],
        config["imutavel"],
    )
    return resultado


def listar_dossies_usuario(user_id: Optional[str]) -> list[dict]:
    """Lista dossiês do usuário com flags de imutabilidade."""
    if not user_id:
        return []
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, case_id, classe, titulo, status,
                       legal_hold, imutavel, created_at,
                       conteudo->>'decisao_final' AS decisao_resumo
                FROM outputs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user_id,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()
