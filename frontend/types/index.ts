// ── Enums de domínio ──────────────────────────────────────────────────────
export type Criticidade       = "critico" | "atencao" | "informativo";
export type GrauConsolidacao  = "Consolidada" | "Majoritária" | "Divergente" | "Emergente";
export type ForcaContraTese   = "Alta" | "Média" | "Baixa";
export type NivelConfianca    = "alto" | "medio" | "baixo";

// ── Resultado de análise RAG (resposta do /v1/analyze) ────────────────────
export interface ResultadoAnalise {
  resposta: string;
  criticidade: Criticidade;
  criticidade_justificativa: string;
  grau_consolidacao: GrauConsolidacao;
  forca_corrente_contraria: ForcaContraTese;
  scoring_confianca: NivelConfianca;
  saidas_stakeholders?: StakeholderOutput[];
  alertas_vigencia?: AlertaVigencia[];
  fontes?: FonteRAG[];
  risco_adocao?: string;
  tokens_usados?: number;
  tempo_ms?: number;
}

export interface StakeholderOutput {
  stakeholder_id: string;
  label: string;
  emoji: string;
  resumo: string;
}

export interface AlertaVigencia {
  mensagem: string;
  alerta: boolean;
}

export interface FonteRAG {
  norma: string;
  artigo: string;
  trecho: string;
  score: number;
}

// ── Dossiê de Decisão ─────────────────────────────────────────────────────
export interface Dossie {
  id: string;
  classe: OutputClasse;
  criado_em: string;
  legal_hold: boolean;
  conteudo_json: Record<string, unknown>;
}

// ── Auth ──────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  nome: string;
  perfil: "ADMIN" | "USER";
  tenant_id: string;
  onboarding_step: number;
}

// ── Tenant ────────────────────────────────────────────────────────────────
export interface Tenant {
  id: string;
  nome: string;
  plano: "trial" | "basico" | "pro" | "enterprise";
  trial_expira_em: string | null;
  ativo: boolean;
}

// ── Cases (Protocolo P1→P6) ───────────────────────────────────────────────
export type CaseStatus =
  | "rascunho"
  | "em_analise"
  | "aguardando_decisao"
  | "decidido"
  | "monitorando"
  | "encerrado";

export interface Case {
  id: string;
  titulo: string;
  descricao: string;
  status: CaseStatus;
  step_atual: number; // 1–6
  criticidade: Criticidade | null;
  criado_em: string;
  atualizado_em: string;
  tenant_id: string;
  user_id: string;
}

export interface CaseStep {
  id: string;
  case_id: string;
  step: number;
  dados: Record<string, unknown>;
  criado_em: string;
}

// ── Outputs ───────────────────────────────────────────────────────────────
export type OutputClasse =
  | "parecer_tecnico"
  | "dossie_decisao"
  | "relatorio_executivo"
  | "mapa_riscos"
  | "plano_acao";

export interface Output {
  id: string;
  case_id: string;
  classe: OutputClasse;
  titulo: string;
  conteudo: string;
  legal_hold: boolean;
  aprovado: boolean;
  criado_em: string;
}

// ── Monitor ───────────────────────────────────────────────────────────────
export interface MonitorFonte {
  id: string;
  nome: string;
  tipo: "dou" | "planalto" | "cgibs" | "nfe" | "rfb" | "sijut2";
  url: string;
  ativa: boolean;
  ultima_verificacao: string | null;
}

export interface MonitorDocumento {
  id: string;
  fonte_id: string;
  titulo: string;
  url: string | null;
  data_publicacao: string | null;
  resumo: string | null;
  lido: boolean;
  criado_em: string;
}

// ── API helpers ───────────────────────────────────────────────────────────
export interface ApiError {
  detail: string;
  status: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
