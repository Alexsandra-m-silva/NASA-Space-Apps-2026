import {
  defaultPreferences,
  type AlertPreferences,
} from "@/data/alerts";
import type {
  GeoLevel,
  ImpactType,
  RiskLevel,
  Territory,
} from "@/data/explore/types";

export const EXPLORE_SEED_KEY = "terrascope.explore.seed.v1";

export type ExploreSeed = {
  preferences: AlertPreferences;
  level: GeoLevel;
  impact: ImpactType | "todos";
  risk: RiskLevel | "todos";
};

export function buildExploreSeed(input: {
  level: GeoLevel;
  impact: ImpactType | "todos";
  risk: RiskLevel | "todos";
  items: Territory[];
}): ExploreSeed {
  const preferences = defaultPreferences();
  const ids = input.items.map((t) => t.id);
  preferences.level = input.level;

  if (input.level === "bioma") preferences.biomas = ids;
  if (input.level === "regiao") preferences.regioes = ids;
  if (input.level === "estado") preferences.estados = ids;
  if (input.level === "municipio") preferences.municipios = ids;

  if (input.impact !== "todos") {
    preferences.impacts = [input.impact];
  } else {
    const set = new Set<ImpactType>();
    input.items.forEach((t) => t.impacts.forEach((i) => set.add(i)));
    preferences.impacts = [...set];
  }

  if (input.risk !== "todos") {
    preferences.risks = [input.risk];
  }
  preferences.alertsEnabled = true;

  return {
    preferences,
    level: input.level,
    impact: input.impact,
    risk: input.risk,
  };
}

export function writeExploreSeed(seed: ExploreSeed) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(EXPLORE_SEED_KEY, JSON.stringify(seed));
}

export function readExploreSeed(): ExploreSeed | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(EXPLORE_SEED_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ExploreSeed;
  } catch {
    return null;
  }
}

export function clearExploreSeed() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(EXPLORE_SEED_KEY);
}

export function consumeExploreSeed(): ExploreSeed | null {
  const seed = readExploreSeed();
  if (seed) clearExploreSeed();
  return seed;
}
