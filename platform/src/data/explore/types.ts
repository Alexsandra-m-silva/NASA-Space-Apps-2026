export type GeoLevel = "bioma" | "regiao" | "estado" | "municipio";

export type RiskLevel = "critico" | "alto" | "moderado";

export type ImpactType =
  | "inseguranca_alimentar"
  | "deficit_hidrico"
  | "perda_renda"
  | "migracao"
  | "pressao_biodiversidade";

export type RankingLens = "tendencia" | "risco" | "impacto" | "carbono";

export type RegeneracaoStatus =
  | "a_recuperar"
  | "em_regeneracao"
  | "regenerado"
  | "protegido";

export type Territory = {
  id: string;
  name: string;
  level: GeoLevel;
  parentId: string | null;
  /** Short code for map regions (UF or region key) */
  mapKey: string;
  /** Trend change in percentage points (surface/desertification index) */
  tendenciaPp: number;
  risk: RiskLevel;
  impacts: ImpactType[];
  /** Cost of inaction over 10 years, BRL millions */
  custoNaoAgirMi: number;
  /** Cost to prevent, BRL millions */
  custoPrevenirMi: number;
  populacaoEstimada: number;
  /** Hectares eligible for regeneration (sample) */
  areaRecuperavelHa: number;
  /**
   * Carbon-credit potential if eligible area is restored.
   * Unit: tCO₂e (1 credit ≈ 1 tCO₂e in the prototype).
   */
  creditosCarbonoTco2e: number;
  regeneracaoStatus: RegeneracaoStatus;
  /** Sample delta since last bulletin, for future email parity */
  mudancaRecente?: {
    tendenciaPp?: number;
    riskFrom?: RiskLevel;
    impactAdded?: ImpactType[];
    impactRemoved?: ImpactType[];
  };
  /** Fields that are labelled estimates (not observed data) */
  estimativas?: string[];
  /** Evidence behind the numbers (MODIS, NISAR, climate, Atlas, susceptibility) */
  dados?: {
    uf?: string;
    area_estudo?: string;
    pct_melhora?: number;
    aquecimento_c_decada?: number;
    aquecimento_significativo?: boolean;
    chuva_1991_2007_mm?: number;
    chuva_2008_2024_mm?: number;
    perda_seca_10a_mi?: number;
    emergencias_reconhecidas_10a?: number;
    nisar?: { pontos: number; auc: number | null; prob_media: number } | null;
    desmatamento_ha_2001_2024?: number | null;
    suscetibilidade_indice?: number | null;
    agregado_de?: string[];
    nota?: string;
  };
};

export const IMPACT_LABELS: Record<ImpactType, string> = {
  inseguranca_alimentar: "Food insecurity",
  deficit_hidrico: "Water deficit",
  perda_renda: "Income / crop loss",
  migracao: "Migration / emergency",
  pressao_biodiversidade: "Pressure on flora and fauna",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  critico: "Critical",
  alto: "High",
  moderado: "Moderate",
};

export const LEVEL_LABELS: Record<GeoLevel, string> = {
  bioma: "Biome",
  regiao: "Region",
  estado: "State",
  municipio: "Municipality",
};

export const REGEN_LABELS: Record<RegeneracaoStatus, string> = {
  a_recuperar: "To restore",
  em_regeneracao: "Regenerating",
  regenerado: "Regenerated",
  protegido: "Protected",
};

export const RISK_ORDER: Record<RiskLevel, number> = {
  critico: 3,
  alto: 2,
  moderado: 1,
};
