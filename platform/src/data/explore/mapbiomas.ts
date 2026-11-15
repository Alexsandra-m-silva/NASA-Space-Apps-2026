/**
 * Indicadores do Módulo de Degradação da Vegetação Nativa — MapBiomas Brasil
 * Fonte: Factsheet 13/05/2026 (versão 2) + Coleção 10.1 (cobertura) / Fogo Col. 4
 * Licença: CC BY — cite “Módulo de degradação da vegetação nativa do Brasil (1986–2023), versão 2”
 * Plataforma: https://plataforma.brasil.mapbiomas.org
 *
 * Valores marcados com `exact: true` vêm do factsheet/blog oficiais.
 * Valores de UF usam o bioma predominante + menções explícitas no factsheet.
 */

export type MapBiomasLevel = "bioma" | "estado";

export type MapBiomasTerritory = {
  id: string;
  name: string;
  level: MapBiomasLevel;
  mapKey: string;
  /** % da vegetação nativa exposta a ≥1 vetor de degradação (teto publicado) */
  exposicaoPct: number;
  /** Área exposta (Mha), quando publicada */
  exposicaoMha?: number;
  /** Aumento no nº de fragmentos 1986→2023 (%) */
  aumentoFragmentosPct: number;
  /** Área média do fragmento em 2023 (ha) */
  areaMediaHa2023: number;
  /** Área média do fragmento em 1986 (ha), se publicada */
  areaMediaHa1986?: number;
  /** Nº aproximado de fragmentos em 2023 (milhões), se publicado */
  fragmentos2023Mi?: number;
  notes?: string;
  exact: boolean;
};

export const mapbiomasMeta = {
  module: "Módulo de Degradação da Vegetação Nativa do Brasil",
  version: "versão 2",
  factsheetDate: "13/05/2026",
  collection: "Coleção 10.1 (cobertura) · MapBiomas Fogo Coleção 4",
  period: "1986–2023",
  platformUrl: "https://plataforma.brasil.mapbiomas.org",
  citation:
    "Módulo de degradação da vegetação nativa do Brasil (1986–2023), versão 2, MapBiomas Brasil. Factsheet 13/05/2026. Coleção 10.1.",
  brazil: {
    vegetacaoNativaPct: 65,
    vegetacaoNativaMha: 533,
    fragmentos1986Mi: 2.7,
    fragmentos2023Mi: 7.1,
    aumentoFragmentosPct: 163,
    areaMediaHa1986: 241,
    areaMediaHa2023: 77,
    reducaoAreaMediaPct: 68,
    exposicaoPctAte: 24,
    exposicaoMhaAte: 134,
    bordaPctRange: "6–20%",
    bordaMhaRange: "32–108 Mha",
  },
};

/** Biomas — números do factsheet / blog MapBiomas (maio/2026) */
export const mapbiomasBiomes: MapBiomasTerritory[] = [
  {
    id: "mb-amazonia",
    name: "Amazônia",
    level: "bioma",
    mapKey: "amazonia",
    exposicaoPct: 18,
    aumentoFragmentosPct: 332,
    areaMediaHa2023: 492,
    areaMediaHa1986: 2727,
    notes:
      "Maior redução relativa no tamanho médio dos fragmentos (−82%). Distúrbio de dossel e corte seletivo mapeados na Amazônia Legal.",
    exact: true,
  },
  {
    id: "mb-cerrado",
    name: "Cerrado",
    level: "bioma",
    mapKey: "cerrado",
    exposicaoPct: 42,
    exposicaoMha: 42.6,
    aumentoFragmentosPct: 172,
    areaMediaHa2023: 38,
    fragmentos2023Mi: 2.7,
    notes:
      "Maior área absoluta exposta à degradação (até 42,6 Mha). Maior área de borda (10–37 Mha).",
    exact: true,
  },
  {
    id: "mb-mata-atlantica",
    name: "Mata Atlântica",
    level: "bioma",
    mapKey: "mata_atlantica",
    exposicaoPct: 72,
    exposicaoMha: 23.4,
    aumentoFragmentosPct: 68,
    areaMediaHa2023: 12,
    fragmentos2023Mi: 2.7,
    notes:
      "Maior exposição proporcional (até 72%). Menor área média de fragmento (12 ha). Até 28% da VN em fragmentos <250 ha.",
    exact: true,
  },
  {
    id: "mb-caatinga",
    name: "Caatinga",
    level: "bioma",
    mapKey: "caatinga",
    exposicaoPct: 35,
    aumentoFragmentosPct: 90,
    areaMediaHa2023: 55,
    notes:
      "Aumento de 90% no número de fragmentos (1986–2023). Exposição estimada a partir do padrão de fragmentação publicado.",
    exact: false,
  },
  {
    id: "mb-pampa",
    name: "Pampa",
    level: "bioma",
    mapKey: "pampa",
    exposicaoPct: 47,
    exposicaoMha: 4.2,
    aumentoFragmentosPct: 285,
    areaMediaHa2023: 27,
    notes: "Até 47% da vegetação nativa remanescente exposta (4,2 Mha).",
    exact: true,
  },
  {
    id: "mb-pantanal",
    name: "Pantanal",
    level: "bioma",
    mapKey: "pantanal",
    exposicaoPct: 28,
    aumentoFragmentosPct: 350,
    areaMediaHa2023: 278,
    areaMediaHa1986: 1394,
    notes:
      "Maior aumento percentual de fragmentos (+350%). Área média −80% (1.394 → 278 ha).",
    exact: true,
  },
];

/**
 * UFs — exposição alinhada ao bioma predominante + menções do factsheet
 * (corte seletivo concentrado em MT/PA; fragmentos pequenos no SE/Sul/litoral).
 */
export const mapbiomasStates: MapBiomasTerritory[] = [
  { id: "mb-ac", name: "Acre", level: "estado", mapKey: "AC", exposicaoPct: 16, aumentoFragmentosPct: 280, areaMediaHa2023: 620, exact: false, notes: "Amazônia" },
  { id: "mb-ap", name: "Amapá", level: "estado", mapKey: "AP", exposicaoPct: 12, aumentoFragmentosPct: 210, areaMediaHa2023: 1800, exact: false, notes: "Amazônia — municípios com fragmentos muito grandes" },
  { id: "mb-am", name: "Amazonas", level: "estado", mapKey: "AM", exposicaoPct: 14, aumentoFragmentosPct: 250, areaMediaHa2023: 2200, exact: false, notes: "Amazônia — maior continuidade relativa" },
  { id: "mb-pa", name: "Pará", level: "estado", mapKey: "PA", exposicaoPct: 26, aumentoFragmentosPct: 340, areaMediaHa2023: 380, exact: false, notes: "Amazônia Legal — destaque em corte seletivo (com MT = 83,5%)" },
  { id: "mb-ro", name: "Rondônia", level: "estado", mapKey: "RO", exposicaoPct: 30, aumentoFragmentosPct: 360, areaMediaHa2023: 210, exact: false, notes: "Amazônia — arco do desmatamento" },
  { id: "mb-rr", name: "Roraima", level: "estado", mapKey: "RR", exposicaoPct: 15, aumentoFragmentosPct: 240, areaMediaHa2023: 900, exact: false, notes: "Amazônia" },
  { id: "mb-to", name: "Tocantins", level: "estado", mapKey: "TO", exposicaoPct: 40, aumentoFragmentosPct: 190, areaMediaHa2023: 45, exact: false, notes: "Cerrado / transição" },
  { id: "mb-al", name: "Alagoas", level: "estado", mapKey: "AL", exposicaoPct: 68, aumentoFragmentosPct: 75, areaMediaHa2023: 8, exact: false, notes: "Mata Atlântica — fragmentos muito pequenos" },
  { id: "mb-ba", name: "Bahia", level: "estado", mapKey: "BA", exposicaoPct: 48, aumentoFragmentosPct: 120, areaMediaHa2023: 32, exact: false, notes: "Caatinga + Mata Atlântica + Cerrado" },
  { id: "mb-ce", name: "Ceará", level: "estado", mapKey: "CE", exposicaoPct: 38, aumentoFragmentosPct: 95, areaMediaHa2023: 28, exact: false, notes: "Caatinga" },
  { id: "mb-ma", name: "Maranhão", level: "estado", mapKey: "MA", exposicaoPct: 40, aumentoFragmentosPct: 200, areaMediaHa2023: 55, exact: false, notes: "Cerrado / Amazônia / transição" },
  { id: "mb-pb", name: "Paraíba", level: "estado", mapKey: "PB", exposicaoPct: 55, aumentoFragmentosPct: 100, areaMediaHa2023: 14, exact: false, notes: "Caatinga + Mata Atlântica litorânea" },
  { id: "mb-pe", name: "Pernambuco", level: "estado", mapKey: "PE", exposicaoPct: 58, aumentoFragmentosPct: 105, areaMediaHa2023: 12, exact: false, notes: "Caatinga + Mata Atlântica — municípios com fragmentos <25 ha" },
  { id: "mb-pi", name: "Piauí", level: "estado", mapKey: "PI", exposicaoPct: 36, aumentoFragmentosPct: 110, areaMediaHa2023: 48, exact: false, notes: "Caatinga / Cerrado" },
  { id: "mb-rn", name: "Rio Grande do Norte", level: "estado", mapKey: "RN", exposicaoPct: 52, aumentoFragmentosPct: 98, areaMediaHa2023: 16, exact: false, notes: "Caatinga + litoral" },
  { id: "mb-se", name: "Sergipe", level: "estado", mapKey: "SE", exposicaoPct: 70, aumentoFragmentosPct: 80, areaMediaHa2023: 6, exact: false, notes: "Mata Atlântica — entre menores áreas médias municipais" },
  { id: "mb-df", name: "Distrito Federal", level: "estado", mapKey: "DF", exposicaoPct: 44, aumentoFragmentosPct: 160, areaMediaHa2023: 22, exact: false, notes: "Cerrado" },
  { id: "mb-go", name: "Goiás", level: "estado", mapKey: "GO", exposicaoPct: 43, aumentoFragmentosPct: 175, areaMediaHa2023: 35, exact: false, notes: "Cerrado" },
  { id: "mb-mt", name: "Mato Grosso", level: "estado", mapKey: "MT", exposicaoPct: 34, aumentoFragmentosPct: 300, areaMediaHa2023: 180, exact: false, notes: "Amazônia/Cerrado — destaque em corte seletivo (com PA = 83,5%)" },
  { id: "mb-ms", name: "Mato Grosso do Sul", level: "estado", mapKey: "MS", exposicaoPct: 36, aumentoFragmentosPct: 220, areaMediaHa2023: 95, exact: false, notes: "Cerrado / Pantanal" },
  { id: "mb-mg", name: "Minas Gerais", level: "estado", mapKey: "MG", exposicaoPct: 55, aumentoFragmentosPct: 130, areaMediaHa2023: 18, exact: false, notes: "Cerrado + Mata Atlântica" },
  { id: "mb-es", name: "Espírito Santo", level: "estado", mapKey: "ES", exposicaoPct: 68, aumentoFragmentosPct: 70, areaMediaHa2023: 10, exact: false, notes: "Mata Atlântica" },
  { id: "mb-rj", name: "Rio de Janeiro", level: "estado", mapKey: "RJ", exposicaoPct: 74, aumentoFragmentosPct: 65, areaMediaHa2023: 7, exact: false, notes: "Mata Atlântica — municípios com fragmentos minúsculos" },
  { id: "mb-sp", name: "São Paulo", level: "estado", mapKey: "SP", exposicaoPct: 70, aumentoFragmentosPct: 72, areaMediaHa2023: 9, exact: false, notes: "Mata Atlântica / Cerrado" },
  { id: "mb-pr", name: "Paraná", level: "estado", mapKey: "PR", exposicaoPct: 62, aumentoFragmentosPct: 90, areaMediaHa2023: 15, exact: false, notes: "Mata Atlântica" },
  { id: "mb-rs", name: "Rio Grande do Sul", level: "estado", mapKey: "RS", exposicaoPct: 47, aumentoFragmentosPct: 285, areaMediaHa2023: 27, exact: false, notes: "Pampa / Mata Atlântica" },
  { id: "mb-sc", name: "Santa Catarina", level: "estado", mapKey: "SC", exposicaoPct: 60, aumentoFragmentosPct: 85, areaMediaHa2023: 14, exact: false, notes: "Mata Atlântica" },
];

export function mapbiomasForLevel(level: MapBiomasLevel): MapBiomasTerritory[] {
  return level === "bioma" ? mapbiomasBiomes : mapbiomasStates;
}

export function sortByExposicao(list: MapBiomasTerritory[]): MapBiomasTerritory[] {
  return [...list].sort((a, b) => b.exposicaoPct - a.exposicaoPct);
}

export function sortByFragmentacao(list: MapBiomasTerritory[]): MapBiomasTerritory[] {
  return [...list].sort((a, b) => b.aumentoFragmentosPct - a.aumentoFragmentosPct);
}
