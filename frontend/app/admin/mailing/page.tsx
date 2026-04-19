"use client";
import { useEffect, useState, useCallback } from "react";
import { Shield, Download, RefreshCw, CheckCircle, Clock, XCircle } from "lucide-react";
import { AdminNav } from "@/components/admin/AdminNav";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";

interface MailingRow {
  id: string;
  email: string;
  nome: string;
  criado_em: string | null;
  empresa: string | null;
  subscription_status: string | null;
  trial_ends_at: string | null;
  trial_expirado: boolean;
  tenant_id: string | null;
  desconto_percentual: number;
}

const FILTROS = [
  { label: "Todos",           value: undefined },
  { label: "Trial ativo",     value: "trial_ativo" },
  { label: "Trial expirado",  value: "trial_expirado" },
  { label: "Convertido",      value: "convertido" },
  { label: "Cancelado",       value: "cancelado" },
] as const;

export default function MailingAdminPage() {
  const [records, setRecords]         = useState<MailingRow[]>([]);
  const [total, setTotal]             = useState(0);
  const [loading, setLoading]         = useState(true);
  const [filtro, setFiltro]           = useState<string | undefined>(undefined);
  const [erro, setErro]               = useState("");
  const [exporting, setExporting]     = useState(false);
  // Controle inline de desconto por tenant_id
  const [descontoEdit, setDescontoEdit]   = useState<Record<string, string>>({});
  const [descontoSaving, setDescontoSaving] = useState<Record<string, boolean>>({});

  const fetchMailing = useCallback(async () => {
    setLoading(true);
    setErro("");
    try {
      const params: Record<string, string> = {};
      if (filtro) params.status = filtro;
      const res = await api.get<{ records: MailingRow[]; total: number }>("/v1/admin/mailing", { params });
      setRecords(res.data.records);
      setTotal(res.data.total);
    } catch {
      setErro("Erro ao carregar dados de mailing.");
    } finally {
      setLoading(false);
    }
  }, [filtro]);

  useEffect(() => { fetchMailing(); }, [fetchMailing]);

  const exportCSV = async () => {
    setExporting(true);
    try {
      const res = await api.get("/v1/admin/mailing/export", { responseType: "blob" });
      const url  = URL.createObjectURL(res.data as Blob);
      const link = document.createElement("a");
      link.href     = url;
      link.download = `mailing_tribus_${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setErro("Erro ao exportar CSV.");
    } finally {
      setExporting(false);
    }
  };

  const salvarDesconto = async (tenantId: string) => {
    const valor = parseFloat(descontoEdit[tenantId] ?? "0");
    if (isNaN(valor) || valor < 0 || valor > 100) return;
    setDescontoSaving((s) => ({ ...s, [tenantId]: true }));
    try {
      await api.patch(`/v1/admin/tenants/${tenantId}/desconto`, { desconto_percentual: valor });
      setRecords((prev) =>
        prev.map((r) => r.tenant_id === tenantId ? { ...r, desconto_percentual: valor } : r)
      );
    } catch {
      setErro("Erro ao salvar desconto.");
    } finally {
      setDescontoSaving((s) => ({ ...s, [tenantId]: false }));
    }
  };

  const statusIcon = (row: MailingRow) => {
    if (row.subscription_status === "active") return <CheckCircle size={13} className="text-emerald-500" aria-label="Convertido" />;
    if (row.trial_expirado)                   return <XCircle size={13} className="text-red-400" aria-label="Trial expirado" />;
    return <Clock size={13} className="text-amber-400" aria-label="Trial ativo" />;
  };

  const statusLabel = (row: MailingRow) => {
    if (row.subscription_status === "active")   return { label: "Convertido",      color: "#10b981" };
    if (row.subscription_status === "canceled") return { label: "Cancelado",       color: "#6b7280" };
    if (row.subscription_status === "past_due") return { label: "Pagamento falhou",color: "#ef4444" };
    if (row.trial_expirado)                     return { label: "Trial expirado",   color: "#f97316" };
    return { label: "Trial ativo", color: "#f59e0b" };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield size={20} className="text-primary" />
          <h1 className="text-2xl font-semibold">Painel Admin</h1>
        </div>
        <Button
          onClick={exportCSV}
          disabled={exporting || total === 0}
          variant="outline"
          className="flex items-center gap-2 text-sm"
        >
          <Download size={14} /> {exporting ? "Exportando…" : "Exportar CSV"}
        </Button>
      </div>

      <AdminNav />

      <div>
        <p className="text-sm text-muted-foreground mb-4">
          Contatos com consentimento LGPD — total: <strong>{total}</strong>
        </p>

        {/* Filtros */}
        <div className="flex flex-wrap gap-1 bg-slate-100 rounded-lg p-1 w-fit mb-4">
          {FILTROS.map((f) => (
            <button
              key={f.label}
              onClick={() => setFiltro(f.value)}
              className="px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer"
              style={filtro === f.value
                ? { background: "#fff", color: "#1F3864", boxShadow: "0 1px 3px rgba(0,0,0,.1)" }
                : { color: "#64748b" }
              }
            >
              {f.label}
            </button>
          ))}
          <button onClick={fetchMailing} className="p-1.5 rounded-md hover:bg-slate-200 transition-colors cursor-pointer">
            <RefreshCw size={13} className="text-slate-500" />
          </button>
        </div>
      </div>

      <Card>
        {erro && <p className="text-sm text-red-500 mb-3">{erro}</p>}
        {loading ? (
          <p className="text-sm text-muted-foreground py-8 text-center">Carregando…</p>
        ) : records.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            Nenhum contato encontrado para este filtro.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: "var(--border,#e2e8f0)" }}>
                  {["", "Nome / E-mail", "Empresa", "Cadastrado em", "Trial expira em", "Status", "Desconto (%)"].map((h) => (
                    <th key={h} className="pb-2 pr-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => {
                  const s = statusLabel(r);
                  return (
                    <tr
                      key={r.id}
                      className="border-b last:border-0 hover:bg-slate-50 transition-colors"
                      style={{ borderColor: "var(--border,#e2e8f0)" }}
                    >
                      <td className="py-3 pr-3">{statusIcon(r)}</td>
                      <td className="py-3 pr-4">
                        <p className="font-medium text-foreground">{r.nome}</p>
                        <p className="text-xs text-muted-foreground">{r.email}</p>
                      </td>
                      <td className="py-3 pr-4 text-xs text-muted-foreground">{r.empresa ?? "—"}</td>
                      <td className="py-3 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                        {r.criado_em ? new Date(r.criado_em).toLocaleDateString("pt-BR") : "—"}
                      </td>
                      <td className="py-3 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                        {r.trial_ends_at ? new Date(r.trial_ends_at).toLocaleDateString("pt-BR") : "—"}
                      </td>
                      <td className="py-3">
                        <span
                          className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                          style={{ background: s.color + "20", color: s.color }}
                        >
                          {s.label}
                        </span>
                      </td>
                      <td className="py-3 pr-2">
                        {r.tenant_id ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              min={0}
                              max={100}
                              step={1}
                              value={descontoEdit[r.tenant_id] ?? String(r.desconto_percentual)}
                              onChange={(e) => setDescontoEdit((d) => ({ ...d, [r.tenant_id!]: e.target.value }))}
                              className="w-14 h-6 text-xs text-center rounded border px-1"
                              style={{ borderColor: "#e2e8f0" }}
                            />
                            <button
                              type="button"
                              disabled={descontoSaving[r.tenant_id]}
                              onClick={() => salvarDesconto(r.tenant_id!)}
                              className="text-[10px] font-semibold px-2 py-1 rounded cursor-pointer transition-colors"
                              style={{ background: "#eff6ff", color: "#2563eb" }}
                            >
                              {descontoSaving[r.tenant_id] ? "…" : "OK"}
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
