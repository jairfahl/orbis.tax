"use client";
import { useProtocoloStore } from "@/store/protocolo";
import { StepIndicator } from "@/components/protocolo/StepIndicator";
import { P1Classificacao } from "@/components/protocolo/P1Classificacao";
import { P2Estruturacao } from "@/components/protocolo/P2Estruturacao";
import { P3Analise } from "@/components/protocolo/P3Analise";
import { P4Hipotese } from "@/components/protocolo/P4Hipotese";
import { P5Decisao } from "@/components/protocolo/P5Decisao";
import { P6Monitoramento } from "@/components/protocolo/P6Monitoramento";

const STEPS = [
  P1Classificacao,
  P2Estruturacao,
  P3Analise,
  P4Hipotese,
  P5Decisao,
  P6Monitoramento,
];

export default function ProtocoloPage() {
  const { stepAtual, reset } = useProtocoloStore();
  const StepComponent = STEPS[stepAtual - 1];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Protocolo de Decisão</h1>
          <p className="text-sm text-muted-foreground mt-1">
            6 passos — auditável e rastreável.
          </p>
        </div>
        <button
          onClick={reset}
          className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
        >
          Nova consulta
        </button>
      </div>

      <StepIndicator atual={stepAtual} />

      <StepComponent />
    </div>
  );
}
