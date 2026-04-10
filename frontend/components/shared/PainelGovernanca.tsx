import { BadgeGrau } from "./BadgeGrau";
import { Disclaimer } from "./Disclaimer";
import type { GrauConsolidacao, ForcaContraTese, NivelConfianca } from "@/types";

const SCORE_COR: Record<NivelConfianca, string> = {
  alto:  "text-emerald-400",
  medio: "text-amber-400",
  baixo: "text-red-400",
};

interface Props {
  grau: GrauConsolidacao;
  forcaContraTese?: ForcaContraTese;
  scoringConfianca?: NivelConfianca;
  risco?: string;
  mostrarDisclaimer?: boolean;
}

export function PainelGovernanca({
  grau,
  forcaContraTese,
  scoringConfianca,
  risco,
  mostrarDisclaimer = true,
}: Props) {
  return (
    <div className="border-t border-border pt-4 mt-4 space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        📊 Governança da Análise
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Grau de Consolidação</p>
          <BadgeGrau grau={grau} />
        </div>

        {forcaContraTese && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">Força da Contra-Tese</p>
            <p className="text-sm font-medium">{forcaContraTese}</p>
          </div>
        )}

        {scoringConfianca && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">Scoring de Confiança</p>
            <p className={`text-sm font-semibold uppercase ${SCORE_COR[scoringConfianca]}`}>
              {scoringConfianca}
            </p>
          </div>
        )}
      </div>

      {risco && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
          <p className="text-xs text-amber-700">⚠ {risco}</p>
        </div>
      )}

      {mostrarDisclaimer && <Disclaimer />}
    </div>
  );
}
