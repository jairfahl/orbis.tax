"use client";
import { useEffect, useState } from "react";
import { FolderOpen, Lock } from "lucide-react";
import { Card } from "@/components/shared/Card";
import api from "@/lib/api";

/* Classe → metadata (matches OutputClass enum in backend) */
const CLASSES: Record<string, { emoji: string; label: string }> = {
  alerta:                  { emoji: "🔔", label: "Alerta" },
  nota_trabalho:           { emoji: "📝", label: "Nota de Trabalho" },
  recomendacao_formal:     { emoji: "📋", label: "Recomendação Formal" },
  dossie_decisao:          { emoji: "📁", label: "Dossiê de Decisão" },
  material_compartilhavel: { emoji: "📤", label: "Material Compartilhável" },
};

/* Classes com legal_hold obrigatório (src/outputs/taxonomia.py) */
const LEGAL_HOLD_CLASSES = new Set(["dossie_decisao", "recomendacao_formal", "material_compartilhavel"]);

interface CaseRow {
  case_id: number;
  titulo: string;
  status: string;
  passo_atual: number;
  created_at: string;
}

interface OutputRow {
  id: number;
  case_id: number;
  classe: string;
  titulo: string;
  conteudo: string;
  created_at: string;
}

interface DocumentoView extends OutputRow {
  case_titulo: string;
}

export default function DocumentosPage() {
  const [documentos, setDocumentos] = useState<DocumentoView[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    async function carregar() {
      try {
        const casesRes = await api.get<CaseRow[]>("/v1/cases");
        const cases = casesRes.data;

        if (cases.length === 0) {
          setDocumentos([]);
          return;
        }

        const outputsPerCase = await Promise.all(
          cases.map((c) =>
            api
              .get<OutputRow[]>(`/v1/cases/${c.case_id}/outputs`)
              .then((r) => r.data.map((o) => ({ ...o, case_titulo: c.titulo })))
              .catch(() => [] as DocumentoView[])
          )
        );

        const flat = outputsPerCase
          .flat()
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

        setDocumentos(flat);
      } catch {
        setErro("Erro ao carregar documentos.");
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  if (loading)
    return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Documentos</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Histórico de análises. Dossiês de Decisão são imutáveis com Legal Hold ativo.
        </p>
      </div>

      {erro && <p className="text-sm text-red-600">{erro}</p>}

      {documentos.length === 0 && !erro ? (
        <div className="text-center py-16 text-muted-foreground">
          <FolderOpen size={36} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">Nenhum documento ainda.</p>
          <p className="text-xs mt-1">
            Complete o protocolo P1→P6 para gerar o primeiro dossiê.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {documentos.map((d) => {
            const cls = CLASSES[d.classe] ?? { emoji: "📄", label: d.classe };
            const legalHold = LEGAL_HOLD_CLASSES.has(d.classe);
            const data = new Date(d.created_at).toLocaleDateString("pt-BR");
            /* Primeira linha não-vazia do conteúdo como preview */
            const preview = d.conteudo
              .split("\n")
              .map((l) => l.replace(/^#+\s*/, "").trim())
              .find((l) => l.length > 0);

            return (
              <Card key={d.id} acento={legalHold ? "primary" : "muted"}>
                <div className="flex items-start gap-3">
                  <span className="text-lg mt-0.5">{cls.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{cls.label}</span>
                      <span className="text-xs text-muted-foreground">· {data}</span>
                      {legalHold && (
                        <span className="inline-flex items-center gap-1 text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                          <Lock size={9} />Legal Hold
                        </span>
                      )}
                      {d.classe === "dossie_decisao" && (
                        <span className="text-xs text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full">
                          🧠 Memória de Decisão
                        </span>
                      )}
                    </div>

                    {d.titulo && (
                      <p className="text-sm font-medium text-foreground mt-1.5 line-clamp-1">
                        {d.titulo}
                      </p>
                    )}

                    {preview && preview !== d.titulo && (
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                        {preview}
                      </p>
                    )}

                    <p className="text-xs text-muted-foreground/60 mt-1">
                      Caso: {d.case_titulo}
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
