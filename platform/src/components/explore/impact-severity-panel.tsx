"use client";

import { useMemo } from "react";
import { ds } from "@/data/design-tokens";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  RISK_ORDER,
  type GeoLevel,
  type ImpactType,
  type Territory,
} from "@/data/explore/types";

type ImpactRow = {
  id: ImpactType;
  label: string;
  score: number;
  territories: number;
  critico: number;
  pct: number;
};

const PIE_COLORS = [
  ds.categorical.A,
  ds.categorical.B,
  ds.categorical.C,
  ds.categorical.D,
  ds.categorical.E,
];

function polar(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function slicePath(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number
) {
  if (endAngle - startAngle >= 359.9) {
    const a = polar(cx, cy, r, startAngle);
    const b = polar(cx, cy, r, startAngle + 180);
    return [
      `M ${cx} ${cy}`,
      `L ${a.x} ${a.y}`,
      `A ${r} ${r} 0 1 1 ${b.x} ${b.y}`,
      `A ${r} ${r} 0 1 1 ${a.x} ${a.y}`,
      "Z",
    ].join(" ");
  }
  const start = polar(cx, cy, r, startAngle);
  const end = polar(cx, cy, r, endAngle);
  const large = endAngle - startAngle > 180 ? 1 : 0;
  return [
    `M ${cx} ${cy}`,
    `L ${start.x} ${start.y}`,
    `A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`,
    "Z",
  ].join(" ");
}

export function ImpactSeverityPanel({
  items,
  level,
  selectedImpact,
  onSelectImpact,
}: {
  items: Territory[];
  level: GeoLevel;
  selectedImpact: ImpactType | "todos";
  onSelectImpact: (impact: ImpactType | "todos") => void;
}) {
  const rows = useMemo(() => {
    const ids = Object.keys(IMPACT_LABELS) as ImpactType[];
    const built = ids.map((id) => {
      const hit = items.filter((t) => t.impacts.includes(id));
      const score = hit.reduce((s, t) => s + RISK_ORDER[t.risk], 0);
      return {
        id,
        label: IMPACT_LABELS[id],
        score,
        territories: hit.length,
        critico: hit.filter((t) => t.risk === "critico").length,
        pct: 0,
      } satisfies ImpactRow;
    });
    const sorted = built
      .filter((r) => r.territories > 0)
      .sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score;
        return b.critico - a.critico;
      });
    const totalScore = sorted.reduce((s, r) => s + r.score, 0) || 1;
    return sorted.map((r) => ({
      ...r,
      pct: (r.score / totalScore) * 100,
    }));
  }, [items]);

  const slices = useMemo(() => {
    let angle = 0;
    return rows.map((row, index) => {
      const sweep = (row.pct / 100) * 360;
      const start = angle;
      const end = angle + sweep;
      angle = end;
      return {
        ...row,
        start,
        end,
        color: PIE_COLORS[index % PIE_COLORS.length],
      };
    });
  }, [rows]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border border-border bg-card p-3 shadow-sm sm:p-4">
      <div className="mb-3">
        <h2 className="font-display text-base text-olive sm:text-lg">
          Impact type · {LEVEL_LABELS[level].toLowerCase()}s
        </h2>
        <p className="mt-0.5 text-[0.7rem] text-muted-foreground sm:text-xs">
          Distribution by severity (most → least critical).
        </p>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-md border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
          No impacts in this view.
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-3">
          <svg
            viewBox="0 0 200 200"
            className="h-36 w-36 shrink-0 sm:h-40 sm:w-40 md:h-44 md:w-44"
            role="img"
            aria-label="Pie chart of impact type distribution"
          >
            {slices.map((s) => {
              const active =
                selectedImpact === "todos" || selectedImpact === s.id;
              return (
                <path
                  key={s.id}
                  d={slicePath(100, 100, 90, s.start, s.end)}
                  fill={s.color}
                  opacity={active ? 1 : 0.35}
                  stroke={ds.neutrals.surface}
                  strokeWidth={2}
                  className="cursor-pointer transition-opacity hover:opacity-90"
                  onClick={() =>
                    onSelectImpact(
                      selectedImpact === s.id ? "todos" : s.id
                    )
                  }
                >
                  <title>
                    {s.label}: {s.pct.toFixed(0)}%
                  </title>
                </path>
              );
            })}
            <circle cx="100" cy="100" r="42" fill={ds.neutrals.surface} />
            <text
              x="100"
              y="96"
              textAnchor="middle"
              className="fill-olive"
              style={{ fontSize: 11, fontWeight: 600 }}
            >
              {rows.length}
            </text>
            <text
              x="100"
              y="112"
              textAnchor="middle"
              className="fill-muted-foreground"
              style={{ fontSize: 9 }}
            >
              types
            </text>
          </svg>

          <ol className="w-full space-y-1">
            {slices.map((s, index) => {
              const active = selectedImpact === s.id;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() =>
                      onSelectImpact(active ? "todos" : s.id)
                    }
                    className={`flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left text-[0.7rem] transition-colors sm:text-xs ${
                      active
                        ? "bg-signal-soft/80"
                        : "hover:bg-secondary/70"
                    }`}
                  >
                    <span
                      className="h-2 w-2 shrink-0 rounded-sm"
                      style={{ background: s.color }}
                    />
                    <span className="min-w-0 flex-1 truncate text-olive">
                      <span className="mr-1 font-display text-muted-foreground">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      {s.label}
                    </span>
                    <span className="shrink-0 text-muted-foreground">
                      {s.pct.toFixed(0)}%
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </div>
  );
}
