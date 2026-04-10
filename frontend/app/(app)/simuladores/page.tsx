"use client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SimuladorCargaRT }        from "@/components/simuladores/SimuladorCargaRT";
import { SimuladorSplitPayment }   from "@/components/simuladores/SimuladorSplitPayment";
import { MonitorCreditos }         from "@/components/simuladores/MonitorCreditos";
import { SimuladorReestruturacao } from "@/components/simuladores/SimuladorReestruturacao";
import { CalculadoraIS }           from "@/components/simuladores/CalculadoraIS";

export default function SimuladoresPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Simuladores</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Impacto da Reforma Tributária no seu negócio.
        </p>
      </div>

      <Tabs defaultValue="carga_rt">
        <TabsList className="bg-muted flex-wrap h-auto gap-1">
          <TabsTrigger value="carga_rt"  className="text-xs">📊 Carga RT</TabsTrigger>
          <TabsTrigger value="split"     className="text-xs">💳 Split Payment</TabsTrigger>
          <TabsTrigger value="creditos"  className="text-xs">🔍 Créditos</TabsTrigger>
          <TabsTrigger value="reest"     className="text-xs">🏭 Reestruturação</TabsTrigger>
          <TabsTrigger value="is"        className="text-xs">⚡ Impacto IS</TabsTrigger>
        </TabsList>
        <TabsContent value="carga_rt"  className="mt-4"><SimuladorCargaRT /></TabsContent>
        <TabsContent value="split"     className="mt-4"><SimuladorSplitPayment /></TabsContent>
        <TabsContent value="creditos"  className="mt-4"><MonitorCreditos /></TabsContent>
        <TabsContent value="reest"     className="mt-4"><SimuladorReestruturacao /></TabsContent>
        <TabsContent value="is"        className="mt-4"><CalculadoraIS /></TabsContent>
      </Tabs>
    </div>
  );
}
