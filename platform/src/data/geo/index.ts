import biomas from "@/data/geo/biomas.json";
import regioes from "@/data/geo/regioes.json";
import estados from "@/data/geo/estados.json";
import type { GeoLevel } from "@/data/explore/types";

export type GeoOption = {
  id: string;
  name: string;
  /** Optional subtitle (e.g. UF sigla) */
  hint?: string;
};

export const IBGE_BIOMAS: GeoOption[] = biomas.map((b) => ({
  id: b.id,
  name: b.name,
}));

export const IBGE_REGIOES: GeoOption[] = regioes.map((r) => ({
  id: r.id,
  name: r.name,
  hint: r.sigla,
}));

export const IBGE_ESTADOS: GeoOption[] = estados.map((e) => ({
  id: e.id,
  name: e.name,
  hint: e.uf,
}));

let municipiosCache: GeoOption[] | null = null;

/** IBGE municipalities (on-demand load — full list). */
export async function loadIbgeMunicipios(): Promise<GeoOption[]> {
  if (municipiosCache) return municipiosCache;
  const mod = await import("@/data/geo/municipios.json");
  const rows = mod.default as { id: string; name: string; ufId: string }[];
  const ufById = new Map(estados.map((e) => [e.id, e.uf]));
  municipiosCache = rows.map((m) => ({
    id: m.id,
    name: m.name,
    hint: ufById.get(m.ufId),
  }));
  return municipiosCache;
}

export function geoOptionsForLevel(level: GeoLevel): GeoOption[] {
  if (level === "bioma") return IBGE_BIOMAS;
  if (level === "regiao") return IBGE_REGIOES;
  if (level === "estado") return IBGE_ESTADOS;
  return [];
}

export const GEO_SOURCE_NOTE =
  "Biomes: official IBGE/MMA classification. Regions, states, and municipalities: IBGE codes.";
