"use client";

import { ds } from "@/data/design-tokens";
import { RISK_LABELS, type RiskLevel, type Territory } from "@/data/explore/types";

/** Schematic Brazil UFs — placeholder heat map for first fold */
const UF_SHAPES: { key: string; label: string; d: string }[] = [
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

function riskColor(risk: RiskLevel | undefined): string {
  if (risk === "critico") return ds.divergent.low;
  if (risk === "alto") return ds.brand.terra;
  if (risk === "moderado") return ds.divergent.lowMid;
  return ds.neutrals.border;
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

export function BrazilMapPlaceholder({
  stateTerritories,
  selectedMapKey,
  onSelectMapKey,
}: {
  stateTerritories: Territory[];
  selectedMapKey: string | null;
  onSelectMapKey: (key: string) => void;
}) {
  const byKey = new Map(stateTerritories.map((t) => [t.mapKey, t]));

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border border-border bg-card p-3 shadow-sm sm:p-4">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="font-display text-base text-olive sm:text-lg">
            Desertification susceptibility under climate stress
          </h2>
        </div>
        <ul className="flex flex-wrap gap-1.5">
          {(
            [
              ["critico", ds.divergent.low],
              ["alto", ds.brand.terra],
              ["moderado", ds.divergent.lowMid],
            ] as const
          ).map(([k, c]) => (
            <li
              key={k}
              className="flex items-center gap-1 text-[0.6rem] text-muted-foreground"
            >
              <span className="h-2 w-2 rounded-sm" style={{ background: c }} />
              {RISK_LABELS[k]}
            </li>
          ))}
        </ul>
      </div>

      <div className="relative mx-auto flex w-full max-w-[340px] flex-1 items-center justify-center md:max-w-[380px]">
        <svg
          viewBox="0 0 380 460"
          className="aspect-[380/460] h-auto max-h-[280px] w-full sm:max-h-[320px] md:max-h-[340px]"
          role="img"
          aria-label="Schematic Brazil heat map by risk"
        >
          <rect width="380" height="460" fill={ds.neutrals.subtle} rx="6" />
          {UF_SHAPES.map((shape) => {
            const t = byKey.get(shape.key);
            const active = selectedMapKey === shape.key;
            const c = centroid(shape.d);
            return (
              <g key={shape.key}>
                <path
                  d={shape.d}
                  fill={riskColor(t?.risk)}
                  stroke={active ? ds.brand.floresta : ds.neutrals.surface}
                  strokeWidth={active ? 2.5 : 1}
                  className="cursor-pointer transition-opacity hover:opacity-90"
                  onClick={() => onSelectMapKey(shape.key)}
                />
                <text
                  x={c.x}
                  y={c.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="pointer-events-none select-none"
                  style={{ fill: ds.brand.areia, fontSize: 9, fontWeight: 600 }}
                >
                  {shape.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
