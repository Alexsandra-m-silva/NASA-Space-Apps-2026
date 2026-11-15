"use client";

import { useMemo } from "react";
import { plural } from "@/lib/utils";
import { ds } from "@/data/design-tokens";
import {
  formatBRLMillions,
  formatCredits,
  formatTrend,
} from "@/data/explore/queries";
import {
  LEVEL_LABELS,
  RISK_LABELS,
  RISK_ORDER,
  type GeoLevel,
  type Territory,
} from "@/data/explore/types";

function BarRow({
  label,
  valueLabel,
  widthPct,
  color,
  active,
  onClick,
}: {
  label: string;
  valueLabel: string;
  widthPct: number;
  color: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-md px-2 py-1.5 text-left transition-colors ${
        active ? "bg-signal-soft/80" : "hover:bg-secondary/70"
      }`}
    >
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="truncate font-medium text-olive">{label}</span>
        <span className="shrink-0 text-muted-foreground">{valueLabel}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-sm bg-muted">
        <div
          className="h-full rounded-sm"
          style={{
            width: `${Math.max(4, widthPct)}%`,
            background: color,
          }}
        />
      </div>
    </button>
  );
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border bg-card p-4 shadow-sm">
      <h3 className="font-display text-base text-olive">{title}</h3>
      <p className="mb-3 text-[0.7rem] text-muted-foreground">{subtitle}</p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

export function RankingCharts({
  items,
  level,
  selectedId,
  onSelect,
}: {
  items: Territory[];
  level: GeoLevel;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const top = useMemo(() => items.slice(0, 8), [items]);

  const byTrend = useMemo(
    () => [...items].sort((a, b) => b.tendenciaPp - a.tendenciaPp).slice(0, 8),
    [items]
  );
  const byRisk = useMemo(
    () =>
      [...items]
        .sort((a, b) => {
          const d = RISK_ORDER[b.risk] - RISK_ORDER[a.risk];
          return d !== 0 ? d : b.tendenciaPp - a.tendenciaPp;
        })
        .slice(0, 8),
    [items]
  );
  const byCarbon = useMemo(
    () =>
      [...items]
        .sort((a, b) => b.creditosCarbonoTco2e - a.creditosCarbonoTco2e)
        .slice(0, 8),
    [items]
  );
  const byCost = useMemo(
    () =>
      [...items]
        .sort((a, b) => b.custoNaoAgirMi - a.custoNaoAgirMi)
        .slice(0, 8),
    [items]
  );

  const maxTrend = Math.max(...byTrend.map((t) => t.tendenciaPp), 1);
  const maxCarbon = Math.max(...byCarbon.map((t) => t.creditosCarbonoTco2e), 1);
  const maxCost = Math.max(...byCost.map((t) => t.custoNaoAgirMi), 1);
  const maxRiskScore = Math.max(
    ...byRisk.map((t) => RISK_ORDER[t.risk] * 10 + t.tendenciaPp),
    1
  );

  if (items.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-card p-10 text-center">
        <p className="font-display text-lg text-olive">
          No chart data for this filter
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <h2 className="font-display text-2xl text-olive">
            Rankings · {plural(LEVEL_LABELS[level].toLowerCase())}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Charts for the current view — click a bar for details.
          </p>
        </div>
        <span className="text-xs text-muted-foreground">
          {items.length} result{items.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ChartCard
          title="Trend"
          subtitle="Change in percentage points (higher = worse)"
        >
          {byTrend.map((t) => (
            <BarRow
              key={`t-${t.id}`}
              label={t.name}
              valueLabel={formatTrend(t.tendenciaPp)}
              widthPct={(t.tendenciaPp / maxTrend) * 100}
              color={ds.divergent.low}
              active={selectedId === t.id}
              onClick={() => onSelect(t.id)}
            />
          ))}
        </ChartCard>

        <ChartCard
          title="Risk"
          subtitle="Sorted critical to moderate"
        >
          {byRisk.map((t) => (
            <BarRow
              key={`r-${t.id}`}
              label={t.name}
              valueLabel={RISK_LABELS[t.risk]}
              widthPct={
                ((RISK_ORDER[t.risk] * 10 + t.tendenciaPp) / maxRiskScore) * 100
              }
              color={
                t.risk === "critico"
                  ? ds.divergent.low
                  : t.risk === "alto"
                    ? ds.brand.terra
                    : ds.divergent.lowMid
              }
              active={selectedId === t.id}
              onClick={() => onSelect(t.id)}
            />
          ))}
        </ChartCard>

        <ChartCard
          title="Carbon"
          subtitle="Credit potential if restored (tCO₂e)"
        >
          {byCarbon.map((t) => (
            <BarRow
              key={`c-${t.id}`}
              label={t.name}
              valueLabel={formatCredits(t.creditosCarbonoTco2e)}
              widthPct={(t.creditosCarbonoTco2e / maxCarbon) * 100}
              color={ds.sequential[4]}
              active={selectedId === t.id}
              onClick={() => onSelect(t.id)}
            />
          ))}
        </ChartCard>

        <ChartCard
          title="Disaster losses 2015–24"
          subtitle="Recorded drought and flood losses, Atlas Digital (S2iD), BRL, inflation-adjusted"
        >
          {byCost.map((t) => (
            <BarRow
              key={`cost-${t.id}`}
              label={t.name}
              valueLabel={formatBRLMillions(t.custoNaoAgirMi)}
              widthPct={(t.custoNaoAgirMi / maxCost) * 100}
              color={ds.brand.floresta}
              active={selectedId === t.id}
              onClick={() => onSelect(t.id)}
            />
          ))}
        </ChartCard>
      </div>

      {top.length > 0 && selectedId && (
        <p className="text-xs text-muted-foreground">
          Territory selected in the charts — see details below.
        </p>
      )}
    </div>
  );
}