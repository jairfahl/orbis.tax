"""
protocol/engine.py — ProtocolStateEngine: máquina de estados P1→P9.

Controla transições, valida dados por passo e mantém audit trail em
case_state_history. Integra CognitiveEngine no P4 e DetectorCarimbo no P6.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import psycopg2
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento de status por passo
# ---------------------------------------------------------------------------
PASSO_STATUS = {
    1: "rascunho",
    2: "em_analise",
    3: "em_analise",
    4: "em_analise",
    5: "aguardando_hipotese",
    6: "em_analise",
    7: "decidido",
    8: "em_monitoramento",
    9: "aprendizado_extraido",
}

PASSO_NOME = {
    1: "Registrar",
    2: "Contextualizar",
    3: "Estruturar",
    4: "Analisar",
    5: "Formular Hipótese",
    6: "Recomendar",
    7: "Decidir",
    8: "Monitorar",
    9: "Aprender",
}

TRANSICOES_VALIDAS: dict[int, list[int]] = {
    1: [2],
    2: [3, 1],
    3: [4, 2],
    4: [5, 3],
    5: [6, 4],
    6: [7, 5],
    7: [8],
    8: [9, 7],
    9: [],
}

# Campos obrigatórios por passo
CAMPOS_OBRIGATORIOS: dict[int, list[str]] = {
    1: ["titulo", "descricao", "contexto_fiscal"],
    2: ["premissas", "periodo_fiscal"],
    3: ["riscos", "dados_qualidade"],
    4: ["query_analise", "analise_result"],
    5: ["hipotese_gestor"],
    6: ["recomendacao"],
    7: ["decisao_final", "decisor"],
    8: ["resultado_real", "data_revisao"],
    9: ["padrao_extraido"],
}


class ProtocolError(ValueError):
    """Erro de validação do protocolo."""


@dataclass
class CaseStep:
    case_id: int
    passo: int
    dados: dict
    concluido: bool
    proximo_passo: Optional[int] = None


@dataclass
class CaseEstado:
    case_id: int
    titulo: str
    status: str
    passo_atual: int
    steps: dict[int, dict]       # passo → {dados, concluido}
    historico: list[dict]
    created_at: str
    updated_at: str


def _get_conn() -> psycopg2.extensions.connection:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL não definida")
    return psycopg2.connect(url)


def _validar_dados_passo(passo: int, dados: dict) -> None:
    """Valida campos obrigatórios e regras específicas por passo."""
    faltando = [c for c in CAMPOS_OBRIGATORIOS[passo] if dados.get(c) is None or dados.get(c) == ""]
    if faltando:
        raise ProtocolError(f"P{passo}: campos obrigatórios ausentes: {faltando}")

    if passo == 1:
        titulo = dados.get("titulo", "")
        if len(str(titulo).strip()) < 10:
            raise ProtocolError("P1: título deve ter no mínimo 10 caracteres")

    if passo == 2:
        premissas = dados.get("premissas", [])
        if not isinstance(premissas, list) or len(premissas) < 2:
            raise ProtocolError("P2: são necessárias pelo menos 2 premissas")

    if passo == 3:
        riscos = dados.get("riscos", [])
        if not isinstance(riscos, list) or len(riscos) < 1:
            raise ProtocolError("P3: pelo menos 1 risco deve ser identificado")


def _registrar_historico(
    cur,
    case_id: int,
    status_de: Optional[str],
    status_para: str,
    passo_de: Optional[int],
    passo_para: int,
    motivo: Optional[str] = None,
) -> None:
    cur.execute(
        """
        INSERT INTO case_state_history
            (case_id, status_de, status_para, passo_de, passo_para, motivo)
        VALUES (%s, %s::case_status, %s::case_status, %s, %s, %s)
        """,
        (case_id, status_de, status_para, passo_de, passo_para, motivo),
    )


class ProtocolStateEngine:

    # ------------------------------------------------------------------
    # Criação de caso
    # ------------------------------------------------------------------
    def criar_caso(self, titulo: str, descricao: str, contexto_fiscal: str) -> int:
        """Cria um novo caso em P1/rascunho. Retorna case_id."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cases (titulo, descricao, status, passo_atual) VALUES (%s, %s, 'rascunho', 1) RETURNING id",
            (titulo, descricao),
        )
        case_id = cur.fetchone()[0]
        # Step P1 inicial com dados parciais
        cur.execute(
            "INSERT INTO case_steps (case_id, passo, dados, concluido) VALUES (%s, 1, %s, FALSE)",
            (case_id, json.dumps({"titulo": titulo, "descricao": descricao, "contexto_fiscal": contexto_fiscal})),
        )
        _registrar_historico(cur, case_id, None, "rascunho", None, 1, "Caso criado")
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Caso criado: id=%d titulo=%s", case_id, titulo)
        return case_id

    # ------------------------------------------------------------------
    # Avanço de passo
    # ------------------------------------------------------------------
    def avancar(self, case_id: int, passo_atual: int, dados: dict) -> CaseStep:
        """
        Conclui passo_atual com dados e avança para o próximo passo.
        Valida pré-condições (incluindo P5→P6) antes de avançar.
        """
        if passo_atual not in TRANSICOES_VALIDAS:
            raise ProtocolError(f"Passo {passo_atual} inválido")

        proximos = TRANSICOES_VALIDAS[passo_atual]
        if not proximos:
            raise ProtocolError(f"P{passo_atual} é o passo terminal (P9). Não há próximo passo.")

        proximo = proximos[0]  # avanço sempre vai para o primeiro da lista

        # 1. Validar dados do passo atual
        _validar_dados_passo(passo_atual, dados)

        conn = _get_conn()
        cur = conn.cursor()

        # 2. Salvar passo atual com concluido=True ANTES de verificar pré-condições do próximo
        cur.execute(
            """
            INSERT INTO case_steps (case_id, passo, dados, concluido)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (case_id, passo) DO UPDATE
                SET dados = EXCLUDED.dados, concluido = TRUE, updated_at = NOW()
            """,
            (case_id, passo_atual, json.dumps(dados)),
        )
        conn.commit()

        # 3. Pré-condição crítica: P6 requer P5 concluído (verificar após salvar P5)
        if proximo == 6:
            self._verificar_p5_concluido(case_id)

        # Criar step do próximo passo (se não existir)
        cur.execute(
            """
            INSERT INTO case_steps (case_id, passo, dados, concluido)
            VALUES (%s, %s, '{}', FALSE)
            ON CONFLICT (case_id, passo) DO NOTHING
            """,
            (case_id, proximo),
        )

        status_de = PASSO_STATUS[passo_atual]
        status_para = PASSO_STATUS[proximo]

        cur.execute(
            "UPDATE cases SET passo_atual=%s, status=%s::case_status, updated_at=NOW() WHERE id=%s",
            (proximo, status_para, case_id),
        )
        _registrar_historico(cur, case_id, status_de, status_para, passo_atual, proximo,
                             f"Passo {passo_atual} concluído")
        conn.commit()
        cur.close()
        conn.close()

        logger.info("Caso %d: P%d → P%d", case_id, passo_atual, proximo)
        return CaseStep(case_id=case_id, passo=proximo, dados={}, concluido=False,
                        proximo_passo=TRANSICOES_VALIDAS[proximo][0] if TRANSICOES_VALIDAS[proximo] else None)

    # ------------------------------------------------------------------
    # Voltar passo
    # ------------------------------------------------------------------
    def voltar(self, case_id: int, passo_atual: int) -> CaseStep:
        """Retrocede ao passo anterior (quando permitido pelas transições)."""
        proximos = TRANSICOES_VALIDAS.get(passo_atual, [])
        if len(proximos) < 2:
            raise ProtocolError(f"P{passo_atual} não permite retroceder")

        anterior = proximos[1]  # segundo elemento = voltar

        conn = _get_conn()
        cur = conn.cursor()
        status_de = PASSO_STATUS[passo_atual]
        status_para = PASSO_STATUS[anterior]

        cur.execute(
            "UPDATE cases SET passo_atual=%s, status=%s::case_status, updated_at=NOW() WHERE id=%s",
            (anterior, status_para, case_id),
        )
        _registrar_historico(cur, case_id, status_de, status_para, passo_atual, anterior,
                             "Retrocesso solicitado")
        conn.commit()
        cur.close()
        conn.close()

        logger.info("Caso %d: P%d ← P%d (voltar)", case_id, anterior, passo_atual)
        return CaseStep(case_id=case_id, passo=anterior, dados={}, concluido=False,
                        proximo_passo=passo_atual)

    # ------------------------------------------------------------------
    # Estado completo do caso
    # ------------------------------------------------------------------
    def get_estado(self, case_id: int) -> CaseEstado:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("SELECT titulo, status, passo_atual, created_at, updated_at FROM cases WHERE id=%s", (case_id,))
        row = cur.fetchone()
        if not row:
            raise ProtocolError(f"Caso {case_id} não encontrado")
        titulo, status, passo_atual, created_at, updated_at = row

        cur.execute("SELECT passo, dados, concluido FROM case_steps WHERE case_id=%s ORDER BY passo", (case_id,))
        steps = {r[0]: {"dados": r[1], "concluido": r[2]} for r in cur.fetchall()}

        cur.execute(
            """SELECT status_de, status_para, passo_de, passo_para, motivo, created_at
               FROM case_state_history WHERE case_id=%s ORDER BY created_at""",
            (case_id,),
        )
        historico = [
            {"status_de": r[0], "status_para": r[1], "passo_de": r[2],
             "passo_para": r[3], "motivo": r[4], "created_at": str(r[5])}
            for r in cur.fetchall()
        ]

        cur.close()
        conn.close()

        return CaseEstado(
            case_id=case_id, titulo=titulo, status=status, passo_atual=passo_atual,
            steps=steps, historico=historico,
            created_at=str(created_at), updated_at=str(updated_at),
        )

    # ------------------------------------------------------------------
    # Verificação
    # ------------------------------------------------------------------
    def pode_avancar(self, case_id: int, passo: int) -> tuple[bool, str]:
        """Retorna (True, '') ou (False, motivo)."""
        proximos = TRANSICOES_VALIDAS.get(passo, [])
        if not proximos:
            return False, f"P{passo} é terminal"
        proximo = proximos[0]
        if proximo == 6:
            try:
                self._verificar_p5_concluido(case_id)
            except ProtocolError as e:
                return False, str(e)
        return True, ""

    def _verificar_p5_concluido(self, case_id: int) -> None:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT concluido FROM case_steps WHERE case_id=%s AND passo=5",
            (case_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or not row[0]:
            raise ProtocolError(
                "P6 requer que P5 (Formular Hipótese) esteja concluído. "
                "O gestor deve registrar sua hipótese antes de ver a recomendação da IA."
            )
