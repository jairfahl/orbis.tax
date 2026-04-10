import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

const PASSOS = [
  { num: 1, label: "Qualificar" },
  { num: 2, label: "Estruturar" },
  { num: 3, label: "Analisar" },
  { num: 4, label: "Hipotetizar" },
  { num: 5, label: "Decidir" },
  { num: 6, label: "Monitorar" },
];

export function StepIndicator({ atual }: { atual: number }) {
  return (
    <div className="flex items-center flex-wrap gap-y-2">
      {PASSOS.map((p, i) => {
        const done = p.num < atual;
        const active = p.num === atual;
        return (
          <div key={p.num} className="flex items-center">
            <div
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
                done && "text-primary",
                active && "bg-primary text-primary-foreground",
                !done && !active && "text-muted-foreground"
              )}
            >
              <span
                className={cn(
                  "flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold",
                  done && "bg-primary text-primary-foreground",
                  active && "bg-primary-foreground text-primary",
                  !done && !active && "border border-border"
                )}
              >
                {done ? <Check size={10} /> : p.num}
              </span>
              <span className="hidden sm:block">{p.label}</span>
            </div>
            {i < PASSOS.length - 1 && (
              <div
                className={cn(
                  "h-px w-3 mx-1",
                  p.num < atual ? "bg-primary" : "bg-border"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
