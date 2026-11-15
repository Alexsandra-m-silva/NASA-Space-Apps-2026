import type {
  GeoLevel,
  ImpactType,
  RankingLens,
  RiskLevel,
} from "@/data/explore/types";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  RISK_LABELS,
} from "@/data/explore/types";
import { geoOptionsForLevel } from "@/data/geo";


export type AlertPreferences = {
  /** Geographic level focus — single select (Território analisado) */
  level: GeoLevel;
  biomas: string[];
  regioes: string[];
  estados: string[];
  municipios: string[];
  /** Empty = nenhum; "todos" na UI preenche todas as chaves */
  impacts: ImpactType[];
  /** Multi-select de níveis de risco (substitui minRisk) */
  risks: RiskLevel[];
  /** @deprecated mantido só para migrar storage antigo */
  minRisk?: RiskLevel | "qualquer";
  lenses: RankingLens[];
  emailMonthly: boolean;
  alertsEnabled: boolean;
};

export type UserProfile = {
  name: string;
  email: string;
  org?: string;
  role: "gestor" | "imprensa" | "ong" | "empresa" | "outro";
  preferences: AlertPreferences;
  onboarded: boolean;
};

export const ROLE_LABELS: Record<UserProfile["role"], string> = {
  gestor: "Government / public sector",
  imprensa: "Journalism / media",
  ong: "NGO / civil society",
  empresa: "Business / private sector",
  outro: "Other",
};

export const LENS_LABELS: Record<RankingLens, string> = {
  tendencia: "Trend",
  risco: "Risk",
  impacto: "Impact type",
  carbono: "Carbon",
};

export const ALL_IMPACTS = Object.keys(IMPACT_LABELS) as ImpactType[];
export const ALL_RISKS = Object.keys(RISK_LABELS) as RiskLevel[];

export const defaultPreferences = (): AlertPreferences => ({
  level: "estado",
  biomas: [],
  regioes: [],
  estados: [],
  municipios: [],
  impacts: [...ALL_IMPACTS],
  risks: [...ALL_RISKS],
  lenses: ["tendencia", "risco"],
  emailMonthly: true,
  alertsEnabled: true,
});

export const STORAGE_KEY = "terrascope.user.v1";

/** Static options per level (municipalities loaded via loadIbgeMunicipios). */
export function optionsForLevel(level: GeoLevel) {
  return geoOptionsForLevel(level);
}

function migrateRisks(raw: Partial<AlertPreferences>): RiskLevel[] {
  if (Array.isArray(raw.risks) && raw.risks.length > 0) {
    return raw.risks.filter((r): r is RiskLevel =>
      ALL_RISKS.includes(r as RiskLevel)
    );
  }
  const legacy = raw.minRisk;
  if (!legacy || legacy === "qualquer") return [...ALL_RISKS];
  if (legacy === "moderado") return ["moderado", "alto", "critico"];
  if (legacy === "alto") return ["alto", "critico"];
  if (legacy === "critico") return ["critico"];
  return [...ALL_RISKS];
}

export function normalizePreferences(
  raw: Partial<AlertPreferences> | null | undefined
): AlertPreferences {
  const base = defaultPreferences();
  if (!raw) return base;
  return {
    ...base,
    ...raw,
    level: raw.level ?? base.level,
    biomas: raw.biomas ?? [],
    regioes: raw.regioes ?? [],
    estados: raw.estados ?? [],
    municipios: raw.municipios ?? [],
    impacts: raw.impacts ?? base.impacts,
    risks: migrateRisks(raw),
    lenses: raw.lenses ?? base.lenses,
    emailMonthly: raw.emailMonthly ?? base.emailMonthly,
    alertsEnabled: raw.alertsEnabled ?? true,
  };
}

export { IMPACT_LABELS, LEVEL_LABELS, RISK_LABELS };
