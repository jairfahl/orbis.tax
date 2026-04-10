import { AlertTriangle, Info, AlertCircle } from "lucide-react";
import type { Criticidade } from "@/types";

const CONFIG = {
  critico:     { label: "CRÍTICO",     icon: AlertTriangle, cls: "bg-red-950 text-red-400 border-red-800" },
  atencao:     { label: "ATENÇÃO",     icon: AlertCircle,   cls: "bg-amber-950 text-amber-400 border-amber-800" },
  informativo: { label: "INFORMATIVO", icon: Info,          cls: "bg-blue-950 text-blue-400 border-blue-800" },
};

export function BadgeCriticidade({
  nivel,
  compacto = false,
}: {
  nivel: Criticidade;
  compacto?: boolean;
}) {
  const c = CONFIG[nivel] ?? CONFIG.informativo;
  const Icon = c.icon;

  if (compacto) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${c.cls}`}
      >
        <Icon size={10} />
        {c.label}
      </span>
    );
  }

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg border ${c.cls}`}>
      <Icon size={16} className="shrink-0" />
      <p className="text-sm font-semibold">{c.label}</p>
    </div>
  );
}
