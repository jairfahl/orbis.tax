import type { GrauConsolidacao } from "@/types";

const CFG: Record<GrauConsolidacao, { emoji: string; cor: string; desc: string }> = {
  "Consolidada": { emoji: "🟢", cor: "text-emerald-400", desc: "Risco mínimo" },
  "Majoritária": { emoji: "🔵", cor: "text-blue-400",    desc: "Risco baixo" },
  "Divergente":  { emoji: "🟠", cor: "text-amber-400",   desc: "Risco moderado a alto" },
  "Emergente":   { emoji: "🔴", cor: "text-red-400",      desc: "Risco alto" },
};

export function BadgeGrau({ grau }: { grau: GrauConsolidacao }) {
  const c = CFG[grau] ?? CFG["Majoritária"];
  return (
    <span className="flex items-center gap-2 text-sm">
      {c.emoji}
      <span className={`font-semibold ${c.cor}`}>{grau}</span>
      <span className="text-muted-foreground text-xs">— {c.desc}</span>
    </span>
  );
}
