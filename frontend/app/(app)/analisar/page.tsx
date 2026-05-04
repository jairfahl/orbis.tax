"use client";
import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send, AlertCircle } from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/shared/Card";
import { BadgeCriticidade } from "@/components/shared/BadgeCriticidade";
import { PainelGovernanca } from "@/components/shared/PainelGovernanca";
import { AnalysisLoading } from "@/components/shared/AnalysisLoading";
import { CTADocumentar } from "@/components/analisar/CTADocumentar";
import { MarkdownText } from "@/components/shared/MarkdownText";
import { ExportPDFButton } from "@/components/shared/ExportPDFButton";
import api from "@/lib/api";
import axios from "axios";
import { useAuthStore } from "@/store/auth";
import type { ResultadoAnalise } from "@/types";

interface LimiteConsultas {
  usado: number;
  limite: number;
  subscription_status: string;
}

export default function AnalisarPage() {
  const { user, isAdmin } = useAuthStore();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<ResultadoAnalise | null>(null);
  const [erro, setErro] = useState<{ tipo: "fora_escopo" | "generico" | "limite"; mensagem: string } | null>(null);
  const [limite, setLimite] = useState<LimiteConsultas | null>(null);

  useEffect(() => {
    if (!user?.id || isAdmin()) return;
    api.get<LimiteConsultas>(`/v1/consultas/limite?user_id=${user.id}`)
      .then((r) => setLimite(r.data))
      .catch(() => {/* silencioso — badge é informativo */});
  }, [user?.id]);

  const limiteEsgotado = limite !== null && limite.limite !== -1 && limite.usado >= limite.limite;

  const limiteBadge = () => {
    if (!limite || limite.limite === -1) return null;
    const restantes = limite.limite - limite.usado;
    const esgotado = restantes <= 0;
    const alerta = restantes === 1;
    return (
      <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
        esgotado
          ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
          : alerta
          ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
          : "bg-muted text-muted-foreground"
      }`}>
        {esgotado
          ? `Limite atingido (${limite.usado}/${limite.limite} consultas no trial)`
          : `${restantes} consulta${restantes !== 1 ? "s" : ""} restante${restantes !== 1 ? "s" : ""} no trial`}
      </span>
    );
  };

  const analisar = async () => {
    if (!query.trim() || limiteEsgotado) return;
    setLoading(true);
    setErro(null);
    setResultado(null);
    try {
      const res = await api.post<ResultadoAnalise>("/v1/analyze", {
        query,
        top_k: topK,
        user_id: user?.id ?? null,
      });
      setResultado(res.data);
      // Atualizar contador local após consulta bem-sucedida
      if (limite && limite.limite !== -1) {
        setLimite((prev) => prev ? { ...prev, usado: prev.usado + 1 } : prev);
      }
    } catch (e: unknown) {
      if (axios.isAxiosError(e) && e.response?.status === 402) {
        setErro({ tipo: "limite", mensagem: "" });
      } else if (axios.isAxiosError(e) && e.response?.status === 400) {
        setErro({ tipo: "fora_escopo", mensagem: "" });
      } else {
        setErro({ tipo: "generico", mensagem: "Erro ao processar. Verifique a conexão com a API." });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Analisar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Fundamentação legislativa da Reforma Tributária em segundos.
          </p>
        </div>
        {limiteBadge()}
      </div>

      {/* Campo de consulta */}
      <Card>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Qual é sua dúvida tributária?
        </label>
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) analisar();
          }}
          placeholder="Descreva sua situação em linguagem natural. Ex: Somos um supermercado no Lucro Real. Como fica nossa carga de IBS/CBS a partir de 2027?"
          className="mt-2 min-h-32 bg-input border-border resize-none text-sm"
        />
        {/* Sugestões rápidas — visíveis apenas quando o campo está vazio */}
        {!query && (
          <div className="flex flex-wrap gap-2 mt-3">
            {[
              "Alíquota de IBS/CBS para serviços de TI",
              "Regime de transição 2026–2032 para indústria",
              "Split payment: quem recolhe o imposto?",
            ].map((sugestao) => (
              <button
                key={sugestao}
                type="button"
                onClick={() => setQuery(sugestao)}
                className="text-xs px-3 py-1.5 rounded-full border transition-colors duration-150 cursor-pointer"
                style={{
                  background: "var(--color-primary-light, #E8F0FA)",
                  border: "1px solid #c3d8f0",
                  color: "var(--color-primary-dark, #1F3864)",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "#d0e4f5";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "var(--color-primary-light, #E8F0FA)";
                }}
              >
                {sugestao}
              </button>
            ))}
          </div>
        )}
        {/* Slider top_k */}
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-medium text-muted-foreground">
              Trechos consultados
            </label>
            <span className="text-xs font-semibold text-primary tabular-nums">{topK}</span>
          </div>
          <input
            type="range"
            min={3}
            max={10}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-border accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-0.5">
            <span>3</span>
            <span className="text-xs text-muted-foreground/60">Mais trechos = resposta mais completa, porém mais lenta</span>
            <span>10</span>
          </div>
        </div>

        <div className="flex justify-between items-center mt-3">
          <p className="text-xs text-muted-foreground">
            {(() => {
              const mod = typeof navigator !== "undefined" && navigator.platform.toUpperCase().includes("MAC") ? "Cmd" : "Ctrl";
              return query.length > 0
                ? `${query.length} caracteres · ${mod}+Enter para analisar`
                : `${mod}+Enter para analisar`;
            })()}
          </p>
          <Button
            onClick={analisar}
            disabled={loading || !query.trim() || limiteEsgotado}
            className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2"
          >
            <Send size={14} />
            {loading ? "Analisando…" : "Analisar"}
          </Button>
        </div>
      </Card>

      {/* Loading */}
      {loading && <AnalysisLoading />}

      {/* Limite trial esgotado */}
      {(erro?.tipo === "limite" || limiteEsgotado) && (
        <Card acento="warning">
          <div className="flex gap-3 items-start">
            <AlertCircle size={18} className="text-amber-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-700">
                Você usou todas as {limite?.limite ?? 5} consultas do seu trial.
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Assine o Orbis para continuar analisando sem limites.
              </p>
              <Link
                href="/assinar"
                className="inline-block mt-2 text-xs font-medium text-primary underline underline-offset-2"
              >
                Ver planos →
              </Link>
            </div>
          </div>
        </Card>
      )}

      {/* Erro fora de escopo */}
      {erro && erro.tipo === "fora_escopo" && (
        <Card>
          <div className="flex gap-3 items-start">
            <AlertCircle size={18} className="text-amber-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-700">
                Essa informação não faz parte do propósito do Orbis.tax.
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Tente uma consulta mais adequada ao ecossistema tributário da Reforma Tributária brasileira — como alíquotas do IVA Dual, regras de CBS/IBS, benefícios fiscais ou impactos setoriais.
              </p>
            </div>
          </div>
        </Card>
      )}
      {erro && erro.tipo === "generico" && (
        <Card acento="danger">
          <p className="text-sm text-red-600">{erro.mensagem}</p>
        </Card>
      )}

      {/* Resultado */}
      {resultado && !loading && (
        <div className="space-y-4">
          <BadgeCriticidade nivel={resultado.criticidade} />

          {resultado.alertas_vigencia
            ?.filter((a) => a.alerta)
            .map((a, i) => (
              <div key={i} className="p-3 tm-card-warning">
                <p className="text-xs tm-text-warning">{a.mensagem}</p>
              </div>
            ))}

          <Card titulo="Análise" acento="primary">
            <MarkdownText text={resultado.resposta} className="text-sm leading-relaxed text-foreground" />
            <PainelGovernanca
              grau={resultado.grau_consolidacao}
              forcaContraTese={resultado.forca_corrente_contraria}
              scoringConfianca={resultado.scoring_confianca}
              risco={resultado.risco_adocao}
              mostrarDisclaimer={false}
            />
          </Card>

          {resultado.saidas_stakeholders && resultado.saidas_stakeholders.length > 0 && (
            <Card titulo="🎯 O que isso significa para cada área">
              <div className="space-y-4">
                {resultado.saidas_stakeholders.map((s) => (
                  <div key={s.stakeholder_id}>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                      {s.emoji} {s.label}
                    </p>
                    <MarkdownText text={s.resumo} className="text-sm leading-relaxed text-foreground" />
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Disclaimer — obrigatório per ESP-06 §2.2 */}
          <p className="text-xs text-muted-foreground border-t border-border pt-3">
            Esta análise é gerada por inteligência artificial com base nas normas da Reforma
            Tributária brasileira (EC 132/2023, LC 214/2025). Não substitui parecer jurídico
            ou consultoria especializada. Verifique a vigência das normas antes de tomar decisões.
          </p>

          {/* Export PDF */}
          <ExportPDFButton sourceType="analysis" analysisData={resultado as unknown as Record<string, unknown>} />

          {/* CTA de documentação — sempre ao final */}
          <CTADocumentar query={query} resultado={resultado} />
        </div>
      )}
    </div>
  );
}
