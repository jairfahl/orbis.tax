"use client";
import { useEffect, useState } from "react";
import { Users, Activity, FileText, Shield } from "lucide-react";
import { Card } from "@/components/shared/Card";
import api from "@/lib/api";

interface AdminMetricas {
  mau_atual: number;
  total_usuarios: number;
  total_analises: number;
  total_dossies: number;
}

export default function AdminPage() {
  const [metricas, setMetricas] = useState<AdminMetricas | null>(null);

  useEffect(() => {
    api.get<AdminMetricas>("/v1/admin/metricas").then((r) => setMetricas(r.data)).catch(console.error);
  }, []);

  const CARDS: { label: string; key: keyof AdminMetricas; icon: React.ElementType }[] = [
    { label: "MAU — Mês atual",     key: "mau_atual",       icon: Activity },
    { label: "Total de usuários",   key: "total_usuarios",  icon: Users },
    { label: "Análises geradas",    key: "total_analises",  icon: FileText },
    { label: "Dossiês registrados", key: "total_dossies",   icon: Shield },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield size={20} className="text-primary" />
        <h1 className="text-2xl font-semibold">Painel Admin</h1>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {CARDS.map(({ label, key, icon: Icon }) => (
          <Card key={key} acento="muted">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
                <p className="text-3xl font-bold mt-1">{metricas ? metricas[key] : "—"}</p>
              </div>
              <Icon size={16} className="text-muted-foreground" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
