import { cn } from "@/lib/utils";

const ACENTOS = {
  primary: "border-l-blue-500",
  success: "border-l-emerald-500",
  warning: "border-l-amber-500",
  danger:  "border-l-red-500",
  muted:   "border-l-slate-600",
};

interface Props {
  children: React.ReactNode;
  className?: string;
  acento?: keyof typeof ACENTOS;
  titulo?: string;
}

export function Card({ children, className, acento, titulo }: Props) {
  return (
    <div
      className={cn(
        "bg-card rounded-lg border border-border p-5",
        acento && `border-l-4 ${ACENTOS[acento]}`,
        className
      )}
    >
      {titulo && (
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          {titulo}
        </p>
      )}
      {children}
    </div>
  );
}
