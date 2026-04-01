"""
tests/unit/test_lockfile.py — Testes do Prompt Integrity Lockfile (RDM-029).

Zero chamadas externas.
"""

import pytest

from src.integrity.lockfile_manager import (
    LockfileMode,
    LockfileStatus,
    calcular_hash,
    gerar_lockfile,
    verificar_integridade,
)


PROMPTS_VALIDOS = {
    "cognitive_system_prompt": (
        "Você é um especialista em tributação da Reforma Tributária brasileira."
    ),
    "outputs_disclaimer": (
        "Este output foi gerado com suporte de inteligência artificial."
    ),
}


class TestCalcularHash:

    def test_hash_deterministico(self):
        h1 = calcular_hash("texto de teste")
        h2 = calcular_hash("texto de teste")
        assert h1 == h2

    def test_hash_64_chars(self):
        h = calcular_hash("qualquer texto")
        assert len(h) == 64

    def test_textos_diferentes_hashes_diferentes(self):
        h1 = calcular_hash("texto A")
        h2 = calcular_hash("texto B")
        assert h1 != h2

    def test_hash_hex_apenas(self):
        h = calcular_hash("teste")
        assert all(c in "0123456789abcdef" for c in h)

    def test_string_vazia(self):
        h = calcular_hash("")
        assert len(h) == 64

    def test_unicode(self):
        h = calcular_hash("alíquota tributária — seção §1º")
        assert len(h) == 64


class TestGerarLockfile:

    def test_lockfile_contem_campos_obrigatorios(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "1.5.0", "U2", "jair")
        assert "id" in lf
        assert "lockfile_hash" in lf
        assert "taxmind_version" in lf
        assert "lockfile_json" in lf
        assert "prompt_ids" in lf
        assert "gate_origem" in lf
        assert "criado_por" in lf

    def test_lockfile_hash_64_chars(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "1.5.0", "U2", "jair")
        assert len(lf["lockfile_hash"]) == 64

    def test_prompt_ids_completos(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "1.5.0", "U2", "jair")
        assert set(lf["prompt_ids"]) == set(PROMPTS_VALIDOS.keys())

    def test_lockfile_json_contem_prompts(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "1.5.0", "U2", "jair")
        assert "prompts" in lf["lockfile_json"]
        for name in PROMPTS_VALIDOS:
            assert name in lf["lockfile_json"]["prompts"]

    def test_lockfile_json_hashes_sao_sha256(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "1.5.0", "U2", "jair")
        for h in lf["lockfile_json"]["prompts"].values():
            assert len(h) == 64

    def test_versao_propagada(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "2.0.0", "U3", "admin")
        assert lf["taxmind_version"] == "2.0.0"
        assert lf["lockfile_json"]["versao"] == "2.0.0"

    def test_gate_propagado(self):
        lf = gerar_lockfile(PROMPTS_VALIDOS, "1.5.0", "CI-prod", "ci")
        assert lf["gate_origem"] == "CI-prod"
        assert lf["lockfile_json"]["gate_origem"] == "CI-prod"

    def test_lockfile_deterministico_em_hashes(self):
        """Mesmos prompts geram mesmos hashes (id e timestamp diferem)."""
        lf1 = gerar_lockfile(PROMPTS_VALIDOS, "1.0.0", "U2", "jair")
        lf2 = gerar_lockfile(PROMPTS_VALIDOS, "1.0.0", "U2", "jair")
        assert lf1["lockfile_json"]["prompts"] == lf2["lockfile_json"]["prompts"]


class TestVerificarIntegridade:

    def _lockfile_json(self, prompts: dict) -> dict:
        return {
            "versao": "1.5.0",
            "gate_origem": "U2",
            "prompts": {name: calcular_hash(c) for name, c in prompts.items()},
        }

    def test_prompts_integros_retorna_valid(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        resultado = verificar_integridade(PROMPTS_VALIDOS, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.VALID
        assert resultado["divergencias"] == []

    def test_prompt_alterado_detecta_divergencia(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_alterados = dict(PROMPTS_VALIDOS)
        prompts_alterados["cognitive_system_prompt"] = "Texto completamente diferente."
        resultado = verificar_integridade(prompts_alterados, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.DIVERGED
        assert len(resultado["divergencias"]) == 1
        assert resultado["divergencias"][0]["tipo"] == "HASH_DIVERGENTE"

    def test_multiplas_divergencias(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_alterados = {
            "cognitive_system_prompt": "alterado 1",
            "outputs_disclaimer": "alterado 2",
        }
        resultado = verificar_integridade(prompts_alterados, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.DIVERGED
        assert len(resultado["divergencias"]) == 2

    def test_modo_block_levanta_exception(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_alterados = {"cognitive_system_prompt": "Conteúdo divergente."}
        with pytest.raises(RuntimeError, match="INTEGRIDADE COMPROMETIDA"):
            verificar_integridade(prompts_alterados, lockfile, LockfileMode.BLOCK)

    def test_prompt_nao_registrado_detectado(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_com_extra = dict(PROMPTS_VALIDOS)
        prompts_com_extra["prompt_novo"] = "Prompt não registrado no lockfile."
        resultado = verificar_integridade(prompts_com_extra, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.DIVERGED
        tipos = [d["tipo"] for d in resultado["divergencias"]]
        assert "PROMPT_NAO_REGISTRADO" in tipos

    def test_modo_warn_nao_levanta_exception(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_alterados = {"cognitive_system_prompt": "Divergente."}
        # Não deve levantar
        resultado = verificar_integridade(prompts_alterados, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.DIVERGED

    def test_lockfile_vazio_tudo_nao_registrado(self):
        lockfile = {"prompts": {}}
        resultado = verificar_integridade(PROMPTS_VALIDOS, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.DIVERGED
        assert all(d["tipo"] == "PROMPT_NAO_REGISTRADO" for d in resultado["divergencias"])

    def test_prompts_vazio_retorna_valid(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        resultado = verificar_integridade({}, lockfile, LockfileMode.WARN)
        assert resultado["status"] == LockfileStatus.VALID

    def test_mensagem_contem_contagem(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_alterados = dict(PROMPTS_VALIDOS)
        prompts_alterados["cognitive_system_prompt"] = "Diferente."
        resultado = verificar_integridade(prompts_alterados, lockfile, LockfileMode.WARN)
        assert "1 divergência(s)" in resultado["mensagem"]

    def test_divergencia_contem_hashes(self):
        lockfile = self._lockfile_json(PROMPTS_VALIDOS)
        prompts_alterados = dict(PROMPTS_VALIDOS)
        prompts_alterados["cognitive_system_prompt"] = "Alterado."
        resultado = verificar_integridade(prompts_alterados, lockfile, LockfileMode.WARN)
        div = resultado["divergencias"][0]
        assert len(div["hash_esperado"]) == 64
        assert len(div["hash_atual"]) == 64
        assert div["hash_esperado"] != div["hash_atual"]
