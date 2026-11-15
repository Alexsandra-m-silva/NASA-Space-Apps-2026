import { territories } from "./territories";
import {
  RISK_ORDER,
  type GeoLevel,
  type ImpactType,
  type RankingLens,
  type RiskLevel,
  type Territory,
} from "./types";

export type ExploreFilters = {
  level: GeoLevel;
  lens: RankingLens;
  impact?: ImpactType | "todos";
  risk?: RiskLevel | "todos";
  selectedId?: string | null;
  query?: string;
};

export function filterTerritories(filters: ExploreFilters): Territory[] {
  let list = territories.filter((t) => t.level === filters.level);

  if (filters.risk && filters.risk !== "todos") {
    list = list.filter((t) => t.risk === filters.risk);
  }

  if (filters.impact && filters.impact !== "todos") {
    list = list.filter((t) => t.impacts.includes(filters.impact as ImpactType));
  }

  if (filters.query?.trim()) {
    const q = filters.query.trim().toLowerCase();
    list = list.filter((t) => t.name.toLowerCase().includes(q));
  }

  return sortByLens(list, filters.lens, filters.impact);
}

export function sortByLens(
  list: Territory[],
  lens: RankingLens,
  impact?: ImpactType | "todos"
): Territory[] {
  const copy = [...list];
  if (lens === "tendencia") {
    return copy.sort((a, b) => b.tendenciaPp - a.tendenciaPp);
  }
  if (lens === "risco") {
    return copy.sort((a, b) => {
      const d = RISK_ORDER[b.risk] - RISK_ORDER[a.risk];
      if (d !== 0) return d;
      return b.tendenciaPp - a.tendenciaPp;
    });
  }
  if (lens === "carbono") {
    return copy.sort((a, b) => b.creditosCarbonoTco2e - a.creditosCarbonoTco2e);
  }
  // impacto: prefer territories that have the selected impact; else by impact count + cost
  return copy.sort((a, b) => {
    if (impact && impact !== "todos") {
      const ai = a.impacts.includes(impact) ? 1 : 0;
      const bi = b.impacts.includes(impact) ? 1 : 0;
      if (bi !== ai) return bi - ai;
    }
    const dCount = b.impacts.length - a.impacts.length;
    if (dCount !== 0) return dCount;
    return b.custoNaoAgirMi - a.custoNaoAgirMi;
  });
}

export function aggregateCost(list: Territory[]): {
  naoAgir: number;
  prevenir: number;
  gap: number;
  creditos: number;
  areaHa: number;
  /** 0–100 transition risk index (ODS 13–aligned sample) */
  transitionRisk: number;
} {
  const naoAgir = list.reduce((s, t) => s + t.custoNaoAgirMi, 0);
  const prevenir = list.reduce((s, t) => s + t.custoPrevenirMi, 0);
  const creditos = list.reduce((s, t) => s + t.creditosCarbonoTco2e, 0);
  const areaHa = list.reduce((s, t) => s + t.areaRecuperavelHa, 0);
  return {
    naoAgir,
    prevenir,
    gap: naoAgir - prevenir,
    creditos,
    areaHa,
    transitionRisk: transitionRiskIndex(list),
  };
}

/**
 * Sample transition-risk index for the filtered slice.
 * Combines desertification trend and risk class into a 0–100 score
 * framed as ODS 13 (Climate Action) transition risk.
 */
export function transitionRiskIndex(list: Territory[]): number {
  if (list.length === 0) return 0;
  const raw =
    list.reduce((s, t) => {
      const trend = Math.min(Math.max(t.tendenciaPp, 0), 12) / 12;
      const risk = RISK_ORDER[t.risk] / 3;
      return s + trend * 0.45 + risk * 0.55;
    }, 0) / list.length;
  return Math.round(Math.min(100, Math.max(0, raw * 100)));
}

export function formatTransitionRisk(score: number): string {
  const n = safeNumber(score);
  if (n == null) return "—";
  return `${Math.round(n)}/100`;
}

/** Severity label for transition risk ≥ 50; null below that threshold. */
export function transitionRiskSeverity(
  score: number
): "Moderado" | "Alto" | "Crítico" | null {
  const n = safeNumber(score);
  if (n == null || n < 50) return null;
  if (n <= 69) return "Moderado";
  if (n <= 89) return "Alto";
  return "Crítico";
}

export function getTerritory(id: string): Territory | undefined {
  return territories.find((t) => t.id === id);
}

export function territoriesForMap(level: GeoLevel): Territory[] {
  // Map paints UF keys primarily; when viewing municipio, still color by parent UF aggregate
  if (level === "municipio" || level === "estado") {
    return territories.filter((t) => t.level === "estado");
  }
  if (level === "regiao") {
    return territories.filter((t) => t.level === "regiao");
  }
  return territories.filter((t) => t.level === "bioma");
}

function safeNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatBRLMillions(value: number): string {
  const n = safeNumber(value);
  if (n == null) return "—";
  if (n >= 1000) {
    return `R$ ${(n / 1000).toFixed(1).replace(".", ",")} bi`;
  }
  if (n >= 100) {
    return `R$ ${Math.round(n)} mi`;
  }
  return `R$ ${n.toFixed(1).replace(".", ",")} mi`;
}

export function formatTrend(pp: number): string {
  const n = safeNumber(pp);
  if (n == null) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1).replace(".", ",")} p.p.`;
}

/** Format tCO₂e / carbon credits for display */
export function formatCredits(tco2e: number): string {
  const n = safeNumber(tco2e);
  if (n == null) return "—";
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1).replace(".", ",")} mi tCO₂e`;
  }
  if (n >= 1_000) {
    return `${Math.round(n / 1_000).toLocaleString("pt-BR")} mil tCO₂e`;
  }
  return `${Math.round(n).toLocaleString("pt-BR")} tCO₂e`;
}

/**
 * Prototype voluntary-market reference price (USD per tCO₂e / credit).
 * Used to turn estimated restoration credits into expected financial impact.
 */
export const CARBON_CREDIT_USD_PER_TCO2E = 15;

export function creditsToUsd(tco2e: number): number {
  const n = safeNumber(tco2e);
  if (n == null) return 0;
  return n * CARBON_CREDIT_USD_PER_TCO2E;
}

/** Format expected financial impact of carbon credits in USD */
export function formatCarbonUsd(tco2e: number): string {
  const usd = creditsToUsd(tco2e);
  if (!Number.isFinite(usd) || usd <= 0) return "—";
  if (usd >= 1_000_000_000) {
    return `$${(usd / 1_000_000_000).toFixed(1)} bn`;
  }
  if (usd >= 1_000_000) {
    return `$${Math.round(usd / 1_000_000).toLocaleString("en-US")} M`;
  }
  if (usd >= 1_000) {
    return `$${Math.round(usd / 1_000).toLocaleString("en-US")} k`;
  }
  return `$${Math.round(usd).toLocaleString("en-US")}`;
}

export function formatHectares(ha: number): string {
  const n = safeNumber(ha);
  if (n == null) return "—";
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(2).replace(".", ",")} mi ha`;
  }
  if (n >= 1000) {
    return `${Math.round(n).toLocaleString("pt-BR")} ha`;
  }
  return `${n.toLocaleString("pt-BR")} ha`;
}
