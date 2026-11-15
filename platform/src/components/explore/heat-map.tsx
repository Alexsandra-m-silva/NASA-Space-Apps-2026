"use client";

import { ds } from "@/data/design-tokens";
import type { GeoLevel, RankingLens, Territory } from "@/data/explore/types";

type MapShape = {
  key: string;
  label: string;
  d: string;
};

/** Schematic NE Brazil — not cartographic accuracy; UX prototype */
const UF_SHAPES: MapShape[] = [
  {
    key: "PI",
    label: "PI",
    d: "M40 70 L120 55 L135 160 L55 175 Z",
  },
  {
    key: "CE",
    label: "CE",
    d: "M120 40 L210 35 L225 110 L135 120 Z",
  },
  {
    key: "RN",
    label: "RN",
    d: "M210 35 L280 50 L270 95 L225 90 Z",
  },
  {
    key: "PB",
    label: "PB",
    d: "M225 95 L275 100 L268 145 L218 140 Z",
  },
  {
    key: "PE",
    label: "PE",
    d: "M135 120 L225 110 L218 165 L125 175 Z",
  },
  {
    key: "BA",
    label: "BA",
    d: "M55 175 L135 160 L125 250 L40 255 Z",
  },
];

const REGION_SHAPES: MapShape[] = [
  {
    key: "sertao",
    label: "Sertão",
    d: "M70 60 L200 50 L210 140 L80 150 Z",
  },
  {
    key: "cariri",
    label: "Cariri",
    d: "M200 90 L270 95 L260 170 L190 165 Z",
  },
  {
    key: "agreste",
    label: "Agreste",
    d: "M80 150 L210 140 L200 220 L70 230 Z",
  },
];

const BIOME_SHAPES: MapShape[] = [
  {
    key: "caatinga",
    label: "Caatinga",
    d: "M50 45 L270 40 L255 230 L45 240 Z",
  },
  {
    key: "cerrado",
    label: "Cerrado*",
    d: "M30 70 L55 65 L50 200 L25 205 Z",
  },
];

function heatColor(
  territory: Territory | undefined,
  lens: RankingLens
): string {
  if (!territory) return ds.neutrals.border;

  if (lens === "risco") {
    if (territory.risk === "critico") return ds.divergent.low;
    if (territory.risk === "alto") return ds.brand.terra;
    return ds.divergent.lowMid;
  }

  if (lens === "impacto") {
    const n = territory.impacts.length;
    if (n >= 4) return ds.divergent.low;
    if (n >= 3) return ds.brand.terra;
    return ds.divergent.lowMid;
  }

  if (lens === "carbono") {
    const c = territory.creditosCarbonoTco2e;
    if (c >= 5_000_000) return ds.sequential[5];
    if (c >= 2_000_000) return ds.sequential[4];
    if (c >= 500_000) return ds.sequential[3];
    return ds.sequential[2];
  }

  // tendencia — escala divergente (pior = laranja)
  const t = territory.tendenciaPp;
  if (t >= 7) return ds.divergent.low;
  if (t >= 5) return ds.brand.terra;
  if (t >= 3) return ds.divergent.lowMid;
  return ds.sequential[2];
}

function pickTerritory(
  shapes: MapShape[],
  mapTerritories: Territory[],
  key: string,
  level: GeoLevel
): Territory | undefined {
  if (level === "bioma" || level === "regiao") {
    return mapTerritories.find((t) => t.mapKey === key);
  }
  return mapTerritories.find((t) => t.mapKey === key && t.level === "estado");
}

export function HeatMap({
  level,
  lens,
  mapTerritories,
  selectedMapKey,
  onSelectMapKey,
}: {
  level: GeoLevel;
  lens: RankingLens;
  mapTerritories: Territory[];
  selectedMapKey: string | null;
  onSelectMapKey: (key: string) => void;
}) {
  const shapes =
    level === "bioma"
      ? BIOME_SHAPES
      : level === "regiao"
        ? REGION_SHAPES
        : UF_SHAPES;

  return (
    <div className="flex h-full flex-col rounded-md border border-border bg-card/90 p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-lg text-olive">Heat map</h2>
          <p className="text-xs text-muted-foreground">
            Dry Northeast schematic · color ={" "}
            {lens === "tendencia"
              ? "trend"
              : lens === "risco"
                ? "risk"
                : lens === "carbono"
                  ? "carbon potential"
                  : "impact intensity"}
          </p>
        </div>
        <Legend lens={lens} />
      </div>

      <div className="relative flex flex-1 items-center justify-center min-h-[280px]">
        <svg
          viewBox="0 0 320 290"
          className="h-full max-h-[420px] w-full"
          role="img"
          aria-label="Schematic Northeast heat map"
        >
          <rect
            x="0"
            y="0"
            width="320"
            height="290"
            fill={ds.neutrals.subtle}
            rx="6"
          />
          {shapes.map((shape) => {
            const t = pickTerritory(shapes, mapTerritories, shape.key, level);
            const active = selectedMapKey === shape.key;
            return (
              <g key={shape.key}>
                <path
                  d={shape.d}
                  fill={heatColor(t, lens)}
                  stroke={active ? ds.brand.floresta : ds.neutrals.surface}
                  strokeWidth={active ? 3 : 1.5}
                  className="cursor-pointer transition-opacity hover:opacity-90"
                  onClick={() => onSelectMapKey(shape.key)}
                />
                <text
                  x={centroidX(shape.d)}
                  y={centroidY(shape.d)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="pointer-events-none select-none fill-primary-foreground text-[11px] font-semibold"
                  style={{ fill: ds.brand.areia }}
                >
                  {shape.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <p className="mt-2 text-[0.7rem] text-muted-foreground">
        Schematic map · data: MODIS 2001–2024 (rainfall removed), NISAR 2026, Atlas Digital, IBGE 2022 — 18 analysed municipalities
      </p>
    </div>
  );
}

function Legend({ lens }: { lens: RankingLens }) {
  const items =
    lens === "risco"
      ? [
          { c: ds.divergent.low, l: "Critical" },
          { c: ds.brand.terra, l: "High" },
          { c: ds.divergent.lowMid, l: "Moderate" },
        ]
      : lens === "impacto"
        ? [
            { c: ds.divergent.low, l: "4+ impacts" },
            { c: ds.brand.terra, l: "3 impacts" },
            { c: ds.divergent.lowMid, l: "1–2 impacts" },
          ]
        : lens === "carbono"
          ? [
              { c: ds.sequential[5], l: "≥ 5M tCO₂e" },
              { c: ds.sequential[4], l: "2–5M" },
              { c: ds.sequential[3], l: "0.5–2M" },
              { c: ds.sequential[2], l: "< 0.5M" },
            ]
          : [
              { c: ds.divergent.low, l: "≥ 7 p.p." },
              { c: ds.brand.terra, l: "5–7 p.p." },
              { c: ds.divergent.lowMid, l: "3–5 p.p." },
              { c: ds.sequential[2], l: "< 3 p.p." },
            ];

  return (
    <ul className="flex flex-wrap justify-end gap-2">
      {items.map((i) => (
        <li key={i.l} className="flex items-center gap-1.5 text-[0.65rem] text-muted-foreground">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ background: i.c }}
          />
          {i.l}
        </li>
      ))}
    </ul>
  );
}

/** Rough centroid from path M/L points — good enough for labels */
function centroidX(d: string): number {
  const pts = [...d.matchAll(/([0-9.]+)\s+([0-9.]+)/g)].map((m) => [
    Number(m[1]),
    Number(m[2]),
  ]);
  if (!pts.length) return 0;
  return pts.reduce((s, p) => s + p[0], 0) / pts.length;
}

function centroidY(d: string): number {
  const pts = [...d.matchAll(/([0-9.]+)\s+([0-9.]+)/g)].map((m) => [
    Number(m[1]),
    Number(m[2]),
  ]);
  if (!pts.length) return 0;
  return pts.reduce((s, p) => s + p[1], 0) / pts.length;
}
