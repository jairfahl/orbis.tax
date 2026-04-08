"""
src/outputs/taxonomia.py — Taxonomia de Saídas (DC v7, G13).

5 classes documentais com regras de imutabilidade, Legal Hold e motor editorial.
Referência: DC v7, Seção: Taxonomia de Saídas — Classes Documentais.
"""

from __future__ import annotations

from src.outputs.engine import OutputClass


# ---------------------------------------------------------------------------
# Configuração DC v7 para cada classe documental
# ---------------------------------------------------------------------------

CLASSES_CONFIG: dict[OutputClass, dict] = {
    OutputClass.ALERTA: {
        "label": "Alerta",
        "emoji": "🔔",
        "descricao": "Notificação breve de mudança normativa ou prazo",
        "compartilhavel": True,
        "legal_hold": False,
        "imutavel": False,
        "pode_promover_para": [OutputClass.NOTA_TRABALHO],
        "pode_rebaixar": True,
    },
    OutputClass.NOTA_TRABALHO: {
        "label": "Nota de Trabalho",
        "emoji": "📝",
        "descricao": "Análise preliminar/exploratória — marcada como rascunho",
        "compartilhavel": False,
        "legal_hold": False,  # apenas se referenciada em decisão
        "imutavel": False,
        "pode_promover_para": [OutputClass.RECOMENDACAO_FORMAL],
        "pode_rebaixar": True,
    },
    OutputClass.RECOMENDACAO_FORMAL: {
        "label": "Recomendação Formal",
        "emoji": "📋",
        "descricao": "Análise completa com fundamentação, contra-tese e grau de consolidação",
        "compartilhavel": True,
        "legal_hold": True,   # obrigatório após aprovação
        "imutavel": False,    # pode ser atualizada antes do P5
        "pode_promover_para": [OutputClass.DOSSIE_DECISAO],
        "pode_rebaixar": True,
    },
    OutputClass.DOSSIE_DECISAO: {
        "label": "Dossiê de Decisão",
        "emoji": "📁",
        "descricao": "Compilação completa: recomendação + premissas + hipótese + decisão",
        "compartilhavel": True,
        "legal_hold": True,   # obrigatório
        "imutavel": True,     # IMUTÁVEL após geração
        "pode_promover_para": [OutputClass.MATERIAL_COMPARTILHAVEL],
        "pode_rebaixar": False,  # REGRA CRÍTICA: não pode rebaixar dossiê
    },
    OutputClass.MATERIAL_COMPARTILHAVEL: {
        "label": "Material Compartilhável",
        "emoji": "📤",
        "descricao": "Output preparado para terceiros (cliente, diretoria, Fisco)",
        "compartilhavel": True,
        "legal_hold": True,
        "imutavel": True,
        "pode_promover_para": [],
        "pode_rebaixar": False,
    },
}


# ---------------------------------------------------------------------------
# Funções de classificação e validação
# ---------------------------------------------------------------------------

def classificar_automaticamente(
    tem_p2: bool,
    tem_p4_hipotese: bool,
    tem_p5_decisao: bool,
    modo_exploracao: bool = False,
) -> OutputClass:
    """
    Classifica automaticamente a saída com base no contexto do protocolo.
    DC v7: "A classificação é atribuída automaticamente com base no contexto."
    """
    if tem_p5_decisao:
        return OutputClass.DOSSIE_DECISAO
    if tem_p4_hipotese and tem_p2:
        return OutputClass.RECOMENDACAO_FORMAL
    if tem_p2 or modo_exploracao:
        return OutputClass.NOTA_TRABALHO
    return OutputClass.ALERTA


def pode_alterar_classe(
    classe_atual: OutputClass,
    classe_destino: OutputClass,
) -> tuple[bool, str]:
    """
    Verifica se a alteração de classe é permitida.
    Returns (permitido, motivo_se_negado).
    """
    config = CLASSES_CONFIG[classe_atual]

    if not config["pode_rebaixar"]:
        destino_config = CLASSES_CONFIG[classe_destino]
        # Comparar por ordem das classes
        _ORDEM = list(OutputClass)
        idx_atual = _ORDEM.index(classe_atual)
        idx_destino = _ORDEM.index(classe_destino)
        if idx_destino < idx_atual:
            return False, (
                f"Não é possível rebaixar um {config['label']}. "
                "Uma vez registrado, este artefato é imutável para auditoria."
            )

    if classe_destino not in config.get("pode_promover_para", []):
        destino_label = CLASSES_CONFIG[classe_destino]["label"]
        return False, f"Não é possível promover diretamente para {destino_label}."

    return True, ""


def get_config(classe: OutputClass) -> dict:
    """Retorna configuração DC v7 para uma classe documental."""
    return CLASSES_CONFIG.get(classe, {})
