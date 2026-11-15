"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CostBanner } from "@/components/explore/cost-banner";
import { ExploreShareActions } from "@/components/explore/explore-actions";
import { ActionCards } from "@/components/explore/action-cards";
import { AskSentinel } from "@/components/explore/ask-sentinel";
import { BrazilMapPlaceholder } from "@/components/explore/brazil-map-placeholder";
import { ImpactSeverityPanel } from "@/components/explore/impact-severity-panel";
import { RankingCharts } from "@/components/explore/ranking-charts";
import { TerritoryDetail } from "@/components/explore/territory-detail";
import { Button } from "@/components/ui/button";
import {
  aggregateCost,
  filterTerritories,
} from "@/data/explore/queries";
import { buildExploreSeed, writeExploreSeed } from "@/data/explore/seed-preferences";
import { territories } from "@/data/explore/territories";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  RISK_LABELS,
  type GeoLevel,
  type ImpactType,
  type RankingLens,
  type RiskLevel,
} from "@/data/explore/types";

const IMPACT_IDS = Object.keys(IMPACT_LABELS) as ImpactType[];
const RISK_IDS = Object.keys(RISK_LABELS) as RiskLevel[];

function parseImpact(v: string | null): ImpactType | "todos" {
  if (!v || v === "todos") return "todos";
  const normalized = v.replace(/-/g, "_") as ImpactType;
  return IMPACT_IDS.includes(normalized) ? normalized : "todos";
}

function parseRisk(v: string | null): RiskLevel | "todos" {
  if (!v || v === "todos") return "todos";
  return RISK_IDS.includes(v as RiskLevel) ? (v as RiskLevel) : "todos";
}

const LEVELS: GeoLevel[] = ["bioma", "regiao", "estado", "municipio"];
const LENSES: { id: RankingLens; label: string }[] = [
  { id: "tendencia", label: "Trend" },
  { id: "risco", label: "Risk" },
  { id: "impacto", label: "Impact type" },
  { id: "carbono", label: "Carbon" },
];

function ChipToggle({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        onClick();
        // Avoid browser scroll-into-view after layout shifts under a focused chip.
        (e.currentTarget as HTMLButtonElement).blur();
      }}
      className={`rounded-md border px-2.5 py-1.5 text-left text-xs transition-colors ${
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-card text-foreground hover:border-primary/40"
      }`}
    >
      {label}
    </button>
  );
}

function parseLevel(v: string | null): GeoLevel {
  return LEVELS.includes(v as GeoLevel) ? (v as GeoLevel) : "estado";
}

function parseLens(v: string | null): RankingLens {
  return (
    ["tendencia", "risco", "impacto", "carbono"] as RankingLens[]
  ).includes(v as RankingLens)
    ? (v as RankingLens)
    : "tendencia";
}

export function ExploreWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [level, setLevel] = useState<GeoLevel>(() =>
    parseLevel(searchParams.get("nivel"))
  );
  const [lens, setLens] = useState<RankingLens>(() =>
    parseLens(searchParams.get("lente"))
  );
  const [impact, setImpact] = useState<ImpactType | "todos">(() =>
    parseImpact(searchParams.get("impacto"))
  );
  const [risk, setRisk] = useState<RiskLevel | "todos">(() =>
    parseRisk(searchParams.get("risco"))
  );
  const [query, setQuery] = useState(() => searchParams.get("q") || "");
  const [selectedId, setSelectedId] = useState<string | null>(
    () => searchParams.get("id")
  );
  const [selectedMapKey, setSelectedMapKey] = useState<string | null>(null);

  const syncUrl = useCallback(
    (next: {
      level: GeoLevel;
      lens: RankingLens;
      impact: ImpactType | "todos";
      risk: RiskLevel | "todos";
      query: string;
      selectedId: string | null;
    }) => {
      const params = new URLSearchParams();
      params.set("nivel", next.level);
      params.set("lente", next.lens);
      if (next.impact !== "todos") params.set("impacto", next.impact);
      if (next.risk !== "todos") params.set("risco", next.risk);
      if (next.query.trim()) params.set("q", next.query.trim());
      if (next.selectedId) params.set("id", next.selectedId);
      const href = `${pathname}?${params.toString()}`;
      const current =
        typeof window !== "undefined"
          ? `${window.location.pathname}${window.location.search}`
          : "";
      if (href === current) return;
      // Keep the viewport still while filters update the query string.
      const y = typeof window !== "undefined" ? window.scrollY : 0;
      router.replace(href, { scroll: false });
      if (typeof window !== "undefined") {
        requestAnimationFrame(() => {
          if (window.scrollY !== y) window.scrollTo(0, y);
        });
      }
    },
    [pathname, router]
  );

  useEffect(() => {
    syncUrl({
      level,
      lens,
      impact,
      risk,
      query,
      selectedId,
    });
  }, [level, lens, impact, risk, query, selectedId, syncUrl]);

  const items = useMemo(
    () =>
      filterTerritories({
        level,
        lens,
        impact,
        risk,
        query,
      }),
    [level, lens, impact, risk, query]
  );

  const stateTerritories = useMemo(
    () => territories.filter((t) => t.level === "estado"),
    []
  );

  const costs = useMemo(() => aggregateCost(items), [items]);

  const selected =
    items.find((t) => t.id === selectedId) ??
    territories.find((t) => t.id === selectedId) ??
    null;

  function handleLevel(next: GeoLevel) {
    setLevel(next);
    setSelectedId(null);
    setSelectedMapKey(null);
  }

  function handleMapKey(key: string) {
    setSelectedMapKey(key);
    const match =
      items.find((t) => t.mapKey === key) ??
      territories.find((t) => t.mapKey === key && t.level === level) ??
      territories.find((t) => t.mapKey === key && t.level === "estado");
    if (match) setSelectedId(match.id);
  }

  function handleSelectTerritory(id: string) {
    setSelectedId(id);
    const t = territories.find((x) => x.id === id);
    if (t) setSelectedMapKey(t.mapKey);
  }

  function handleAlertsCta() {
    writeExploreSeed(
      buildExploreSeed({
        level,
        impact,
        risk,
        items,
      })
    );
  }

  const alertsHref = "/newsletter?from=explore";

  return (
    <div data-header-contrast="light" className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-border/80 pb-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
          <div className="min-w-0 flex-1">
            <p className="text-[0.7rem] uppercase tracking-[0.2em] text-signal">
              Explore
            </p>
            <h1 className="mt-1 font-display text-3xl text-olive sm:text-4xl">
              See impact and insights about desertification susceptibility
            </h1>
          </div>
          <div className="flex shrink-0 justify-end self-end">
            <ExploreShareActions items={items} level={level} lens={lens} />
          </div>
        </div>
      </div>

      <CostBanner
        creditos={costs.creditos}
        areaHa={costs.areaHa}
        transitionRisk={costs.transitionRisk}
      />

      {/* Filters — chip buttons, same pattern as newsletter preferences */}
      <div className="space-y-6 rounded-md border border-border bg-card/80 p-3 sm:p-4">
        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Territory analyzed
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            {LEVELS.map((l) => (
              <ChipToggle
                key={l}
                label={LEVEL_LABELS[l]}
                active={level === l}
                onClick={() => handleLevel(l)}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Chart sort order
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            {LENSES.map((l) => (
              <ChipToggle
                key={l.id}
                label={l.label}
                active={lens === l.id}
                onClick={() => setLens(l.id)}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Impact type
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            <ChipToggle
              label="All"
              active={impact === "todos"}
              onClick={() => setImpact("todos")}
            />
            {(Object.keys(IMPACT_LABELS) as ImpactType[]).map((k) => (
              <ChipToggle
                key={k}
                label={IMPACT_LABELS[k]}
                active={impact === k}
                onClick={() => setImpact(k)}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Risk
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            <ChipToggle
              label="All"
              active={risk === "todos"}
              onClick={() => setRisk("todos")}
            />
            {(Object.keys(RISK_LABELS) as RiskLevel[]).map((k) => (
              <ChipToggle
                key={k}
                label={RISK_LABELS[k]}
                active={risk === k}
                onClick={() => setRisk(k)}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Search
          </legend>
          <input
            className="mt-3 h-10 w-full max-w-md rounded-md border border-input bg-background px-3 text-sm"
            placeholder="Territory name"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </fieldset>
      </div>

      {/* ——— First fold: map + Exploration focus ——— */}
      <section
        aria-label="First fold — map and actions"
        className="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]"
      >
        <div className="min-w-0">
          <BrazilMapPlaceholder
            stateTerritories={stateTerritories}
            selectedMapKey={selectedMapKey}
            onSelectMapKey={handleMapKey}
          />
        </div>
        <div className="min-w-0 md:max-h-[520px]">
          <ActionCards
            items={items}
            level={level}
            impact={impact}
            risk={risk}
          />
        </div>
      </section>

      <AskSentinel
        items={items}
        level={level}
        impact={impact}
        risk={risk}
      />

      {/* ——— Second fold: impact type ——— */}
      <section
        aria-label="Second fold — impact type"
        className="space-y-8 border-t border-border pt-10"
      >
        <div className="min-w-0">
          <ImpactSeverityPanel
            items={items}
            level={level}
            selectedImpact={impact}
            onSelectImpact={setImpact}
          />
        </div>

        <RankingCharts
          items={items}
          level={level}
          selectedId={selectedId}
          onSelect={handleSelectTerritory}
        />
        <div>
          <TerritoryDetail territory={selected} />
        </div>
      </section>

      {/* CTA — filters seed into prefs */}
      <section className="rounded-md border border-border bg-card/80 px-5 py-6 sm:px-7">
        <h2 className="font-display text-xl text-olive">
          Need a heads-up when the evidence changes?
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Subscribe to the email newsletter — for newsrooms, cabinets, or risk
          desks. Filters from this page are pre-selected.
        </p>
        <div className="mt-4">
          <Button asChild variant="ghost">
            <Link href={alertsHref} onClick={handleAlertsCta}>
              Go to the newsletter
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
