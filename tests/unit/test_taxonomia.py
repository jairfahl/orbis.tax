"""
tests/unit/test_taxonomia.py — Testes unitários da Taxonomia de Saídas (G13).

Verifica 5 classes, regras de imutabilidade e classificação automática.
Nenhuma chamada externa.
"""

from src.outputs.taxonomia import (
    CLASSES_CONFIG,
    OutputClass,
    classificar_automaticamente,
    pode_alterar_classe,
)


def test_cinco_classes_definidas():
    assert len(CLASSES_CONFIG) == 5


def test_dossie_imutavel():
    config = CLASSES_CONFIG[OutputClass.DOSSIE_DECISAO]
    assert config["imutavel"] is True
    assert config["legal_hold"] is True
    assert config["pode_rebaixar"] is False


def test_alerta_nao_imutavel():
    config = CLASSES_CONFIG[OutputClass.ALERTA]
    assert config["imutavel"] is False
    assert config["legal_hold"] is False


def test_classificar_p5_gera_dossie():
    classe = classificar_automaticamente(
        tem_p2=True, tem_p4_hipotese=True, tem_p5_decisao=True
    )
    assert classe == OutputClass.DOSSIE_DECISAO


def test_classificar_p4_sem_p5_gera_recomendacao():
    classe = classificar_automaticamente(
        tem_p2=True, tem_p4_hipotese=True, tem_p5_decisao=False
    )
    assert classe == OutputClass.RECOMENDACAO_FORMAL


def test_classificar_apenas_p2_gera_nota():
    classe = classificar_automaticamente(
        tem_p2=True, tem_p4_hipotese=False, tem_p5_decisao=False
    )
    assert classe == OutputClass.NOTA_TRABALHO


def test_nao_pode_rebaixar_dossie():
    ok, motivo = pode_alterar_classe(
        OutputClass.DOSSIE_DECISAO,
        OutputClass.NOTA_TRABALHO,
    )
    assert ok is False
    assert "imutável" in motivo.lower()
