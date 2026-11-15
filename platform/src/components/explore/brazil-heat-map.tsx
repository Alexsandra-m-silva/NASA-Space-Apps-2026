"use client";

import { ds } from "@/data/design-tokens";
import type { MapBiomasTerritory } from "@/data/explore/mapbiomas";

type Shape = { key: string; label: string; d: string };

/** Schematic Brazil — UX prototype, not IBGE cartography */
const UF_SHAPES: Shape[] = [
  { key: "RR", label: "RR", d: "M118 28 L168 22 L175 70 L125 78 Z" },
  { key: "AP", label: "AP", d: "M175 22 L210 30 L205 70 L175 68 Z" },
  { key: "AM", label: "AM", d: "M40 70 L125 55 L168 95 L95 140 L35 120 Z" },
  { key: "PA", label: "PA", d: "M168 70 L230 55 L255 110 L200 145 L155 120 Z" },
  { key: "AC", label: "AC", d: "M18 120 L55 115 L70 150 L28 158 Z" },
  { key: "RO", label: "RO", d: "M70 140 L110 135 L118 175 L75 180 Z" },
  { key: "MT", label: "MT", d: "M110 145 L175 135 L185 205 L115 210 Z" },
  { key: "TO", label: "TO", d: "M200 145 L235 140 L240 195 L205 198 Z" },
  { key: "MA", label: "MA", d: "M240 95 L285 90 L290 145 L245 150 Z" },
  { key: "PI", label: "PI", d: "M245 150 L285 145 L288 195 L250 198 Z" },
  { key: "CE", label: "CE", d: "M288 120 L330 115 L335 155 L292 158 Z" },
  { key: "RN", label: "RN", d: "M330 118 L358 125 L352 148 L330 145 Z" },
  { key: "PB", label: "PB", d: "M325 148 L352 150 L348 168 L322 165 Z" },
  { key: "PE", label: "PE", d: "M300 158 L345 165 L338 185 L295 178 Z" },
  { key: "AL", label: "AL", d: "M320 178 L348 182 L342 198 L318 192 Z" },
  { key: "SE", label: "SE", d: "M305 188 L330 195 L325 210 L300 205 Z" },
  { key: "BA", label: "BA", d: "M250 198 L310 190 L320 270 L245 265 Z" },
  { key: "DF", label: "DF", d: "M198 220 L212 218 L214 232 L200 234 Z" },
  { key: "GO", label: "GO", d: "M175 205 L235 200 L240 255 L180 258 Z" },
  { key: "MG", label: "MG", d: "M235 230 L310 225 L315 290 L240 295 Z" },
  { key: "ES", label: "ES", d: "M315 255 L340 260 L335 295 L312 290 Z" },
  { key: "RJ", label: "RJ", d: "M295 295 L330 300 L325 320 L290 315 Z" },
  { key: "SP", label: "SP", d: "M210 280 L290 275 L295 315 L215 320 Z" },
  { key: "MS", label: "MS", d: "M140 230 L185 225 L190 290 L145 295 Z" },
  { key: "PR", label: "PR", d: "M195 320 L265 315 L270 350 L200 355 Z" },
  { key: "SC", label: "SC", d: "M210 350 L265 348 L268 375 L215 378 Z" },
  { key: "RS", label: "RS", d: "M185 375 L260 372 L255 430 L175 425 Z" },
];

const BIOME_SHAPES: Shape[] = [
  { key: "amazonia", label: "Amazon", d: "M25 40 L230 35 L250 150 L100 175 L30 130 Z" },
  { key: "cerrado", label: "Cerrado", d: "M150 150 L255 145 L270 270 L160 275 Z" },
  { key: "caatinga", label: "Caatinga", d: "M255 120 L340 115 L345 210 L265 215 Z" },
  { key: "mata_atlantica", label: "Atl. Forest", d: "M230 230 L340 220 L345 380 L220 390 L210 300 Z" },
  { key: "pantanal", label: "Pantanal", d: "M130 220 L175 215 L180 270 L135 275 Z" },
  { key: "pampa", label: "Pampa", d: "M175 375 L260 370 L255 430 L170 425 Z" },
];

function heat(exposicaoPct: number | undefined): string {
  if (exposicaoPct == null) return ds.neutrals.border;
  if (exposicaoPct >= 65) return ds.divergent.low;
  if (exposicaoPct >= 45) return ds.brand.terra;
  if (exposicaoPct >= 30) return ds.divergent.lowMid;
  if (exposicaoPct >= 18) return ds.sequential[3];
  return ds.sequential[2];
}

function centroid(d: string): { x: number; y: number } {
  const pts = [...d.matchAll(/([0-9.]+)\s+([0-9.]+)/g)].map((m) => [
    Number(m[1]),
    Number(m[2]),
  ]);
  if (!pts.length) return { x: 0, y: 0 };
  return {
    x: pts.reduce((s, p) => s + p[0], 0) / pts.length,
    y: pts.reduce((s, p) => s + p[1], 0) / pts.length,
  };
}

export function BrazilHeatMap({
  level,
  territories,
  selectedKey,
  onSelect,
}: {
  level: "bioma" | "estado";
  territories: MapBiomasTerritory[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}) {
  const shapes = level === "bioma" ? BIOME_SHAPES : UF_SHAPES;
  const byKey = new Map(territories.map((t) => [t.mapKey, t]));

  return (
    <div className="flex h-full flex-col rounded-md border border-border bg-card/90 p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-lg text-olive">
            Heat map · degradation
          </h2>
          <p className="text-xs text-muted-foreground">
            Native vegetation exposure to degradation drivers (MapBiomas)
          </p>
        </div>
        <ul className="flex flex-wrap justify-end gap-2">
          {[
            { c: ds.divergent.low, l: "≥ 65%" },
            { c: ds.brand.terra, l: "45–65%" },
            { c: ds.divergent.lowMid, l: "30–45%" },
            { c: ds.sequential[3], l: "18–30%" },
            { c: ds.sequential[2], l: "< 18%" },
          ].map((i) => (
            <li
              key={i.l}
              className="flex items-center gap-1.5 text-[0.65rem] text-muted-foreground"
            >
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.c }} />
              {i.l}
            </li>
          ))}
        </ul>
      </div>

      <div className="relative flex min-h-[320px] flex-1 items-center justify-center">
        <svg
          viewBox="0 0 380 460"
          className="h-full max-h-[480px] w-full"
          role="img"
          aria-label="Heat map of native vegetation degradation in Brazil"
        >
          <rect width="380" height="460" fill={ds.neutrals.subtle} rx="6" />
          {shapes.map((shape) => {
            const t = byKey.get(shape.key);
            const active = selectedKey === shape.key;
            const c = centroid(shape.d);
            return (
              <g key={shape.key}>
                <path
                  d={shape.d}
                  fill={heat(t?.exposicaoPct)}
                  stroke={active ? ds.brand.floresta : ds.neutrals.surface}
                  strokeWidth={active ? 2.5 : 1}
                  className="cursor-pointer transition-opacity hover:opacity-90"
                  onClick={() => onSelect(shape.key)}
                />
                <text
                  x={c.x}
                  y={c.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="pointer-events-none select-none"
                  style={{
                    fill: ds.brand.areia,
                    fontSize: level === "bioma" ? 11 : 9,
                    fontWeight: 600,
                  }}
                >
                  {shape.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <p className="mt-2 text-[0.7rem] leading-relaxed text-muted-foreground">
        Simplified cartographic schematic. Data: MapBiomas Degradation v2 · Col.
        10.1 · Factsheet 13/05/2026 (CC BY).
      </p>
    </div>
  );
}
