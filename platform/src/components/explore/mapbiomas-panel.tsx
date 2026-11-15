"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BrazilHeatMap } from "@/components/explore/brazil-heat-map";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  mapbiomasForLevel,
  mapbiomasMeta,
  sortByExposicao,
  sortByFragmentacao,
  type MapBiomasLevel,
  type MapBiomasTerritory,
} from "@/data/explore/mapbiomas";

type SortMode = "exposicao" | "fragmentacao";

export function MapBiomasPanel() {
  const [level, setLevel] = useState<MapBiomasLevel>("bioma");
  const [sort, setSort] = useState<SortMode>("exposicao");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const items = useMemo(() => {
    const list = mapbiomasForLevel(level);
    return sort === "exposicao"
      ? sortByExposicao(list)
      : sortByFragmentacao(list);
  }, [level, sort]);

  const selected =
    items.find((t) => t.mapKey === selectedKey) ??
    items.find((t) => t.id === selectedKey) ??
    null;

  function selectKey(key: string) {
    setSelectedKey(key);
  }

  function selectTerritory(t: MapBiomasTerritory) {
    setSelectedKey(t.mapKey);
  }

  const br = mapbiomasMeta.brazil;

  return (
    <div className="space-y-5">
      <div className="rounded-md border border-signal/30 bg-signal-soft/50 px-4 py-4 sm:px-5">
        <p className="text-[0.7rem] uppercase tracking-[0.16em] text-signal">
          Source · MapBiomas Brazil
        </p>
        <h2 className="mt-1 font-display text-xl text-olive sm:text-2xl">
          {mapbiomasMeta.module}
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
          {mapbiomasMeta.version} · Factsheet {mapbiomasMeta.factsheetDate} ·{" "}
          {mapbiomasMeta.collection} · period {mapbiomasMeta.period}. In Brazil,{" "}
          <strong className="text-foreground">{br.vegetacaoNativaPct}%</strong> of
          the territory was native vegetation in 2023 ({br.vegetacaoNativaMha} Mha).
          Fragments: {br.fragmentos1986Mi} M (1986) → {br.fragmentos2023Mi} M
          (2023), <strong className="text-foreground">+{br.aumentoFragmentosPct}%</strong>.
          Up to <strong className="text-foreground">{br.exposicaoPctAte}%</strong> of
          native vegetation ({br.exposicaoMhaAte} Mha) exposed to ≥1 degradation driver.
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          Cite: {mapbiomasMeta.citation}{" "}
          <a
            href={mapbiomasMeta.platformUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline-offset-2 hover:underline"
          >
            Open MapBiomas platform
          </a>
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded-md border border-border bg-card/80 p-3 sm:p-4">
        <div className="flex flex-wrap gap-2">
          <span className="self-center text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Level
          </span>
          {(["bioma", "estado"] as MapBiomasLevel[]).map((l) => (
            <Button
              key={l}
              type="button"
              size="sm"
              variant={level === l ? "default" : "outline"}
              onClick={() => {
                setLevel(l);
                setSelectedKey(null);
              }}
            >
              {l === "bioma" ? "Biome" : "State"}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="self-center text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Rank by
          </span>
          <Button
            type="button"
            size="sm"
            variant={sort === "exposicao" ? "default" : "outline"}
            onClick={() => setSort("exposicao")}
          >
            Degradation exposure
          </Button>
          <Button
            type="button"
            size="sm"
            variant={sort === "fragmentacao" ? "default" : "outline"}
            onClick={() => setSort("fragmentacao")}
          >
            Fragment increase
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <BrazilHeatMap
          level={level}
          territories={items}
          selectedKey={selectedKey}
          onSelect={selectKey}
        />

        <div className="space-y-4">
          <div>
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h3 className="font-display text-lg text-olive">
                Ranking · {level === "bioma" ? "biomes" : "states"}
              </h3>
              <span className="text-xs text-muted-foreground">
                {items.length} territories
              </span>
            </div>
            <ol className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
              {items.map((t, i) => {
                const active = selected?.id === t.id;
                return (
                  <li key={t.id}>
                    <button
                      type="button"
                      onClick={() => selectTerritory(t)}
                      className={`flex w-full items-start gap-3 rounded-md border px-3 py-3 text-left transition-all ${
                        active
                          ? "border-primary bg-signal-soft shadow-sm"
                          : "border-border bg-card/90 hover:border-primary/40"
                      }`}
                    >
                      <span className="mt-0.5 w-6 shrink-0 font-display text-sm text-muted-foreground">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-display text-base text-olive">
                            {t.name}
                          </span>
                          {!t.exact && (
                            <Badge variant="outline" className="text-[0.65rem]">
                              derived
                            </Badge>
                          )}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          <span>
                            Exposure{" "}
                            <strong className="text-foreground">
                              up to {t.exposicaoPct}%
                            </strong>
                            {t.exposicaoMha != null
                              ? ` (${t.exposicaoMha} Mha)`
                              : ""}
                          </span>
                          <span>
                            Fragments{" "}
                            <strong className="text-foreground">
                              +{t.aumentoFragmentosPct}%
                            </strong>
                          </span>
                          <span>
                            Mean area{" "}
                            <strong className="text-foreground">
                              {t.areaMediaHa2023.toLocaleString("en-US")} ha
                            </strong>
                          </span>
                        </div>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>

          {selected ? (
            <article className="animate-rise rounded-md border border-border bg-card p-5 shadow-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">
                  {selected.level === "bioma" ? "Biome" : "State"}
                </Badge>
                <Badge
                  className={
                    selected.exact
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }
                >
                  {selected.exact ? "Factsheet" : "Derived from biome"}
                </Badge>
              </div>
              <h3 className="mt-2 font-display text-2xl text-olive">
                {selected.name}
              </h3>
              <dl className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-md bg-signal-soft/70 px-3 py-2">
                  <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
                    Degradation exposure
                  </dt>
                  <dd className="font-display text-xl text-primary">
                    up to {selected.exposicaoPct}%
                  </dd>
                </div>
                <div className="rounded-md bg-secondary/70 px-3 py-2">
                  <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
                    ↑ fragments 1986–2023
                  </dt>
                  <dd className="font-display text-xl">
                    +{selected.aumentoFragmentosPct}%
                  </dd>
                </div>
                <div className="rounded-md border border-border px-3 py-2">
                  <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
                    Mean area 2023
                  </dt>
                  <dd className="font-display text-lg">
                    {selected.areaMediaHa2023.toLocaleString("en-US")} ha
                  </dd>
                </div>
                <div className="rounded-md border border-border px-3 py-2">
                  <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
                    Mean area 1986
                  </dt>
                  <dd className="font-display text-lg">
                    {selected.areaMediaHa1986
                      ? `${selected.areaMediaHa1986.toLocaleString("en-US")} ha`
                      : "—"}
                  </dd>
                </div>
              </dl>
              {selected.notes && (
                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                  {selected.notes}
                </p>
              )}
            </article>
          ) : (
            <div className="rounded-md border border-dashed border-border bg-card/60 p-5 text-sm text-muted-foreground">
              Select a biome or state on the map or in the ranking to view
              degradation indicators.
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        States marked “derived” use the predominant biome and factsheet mentions
        (e.g. selective logging in MT/PA). For official municipal series, use the{" "}
        <Link
          href={mapbiomasMeta.platformUrl}
          className="text-primary underline-offset-2 hover:underline"
          target="_blank"
        >
          MapBiomas platform
        </Link>
        .
      </p>
    </div>
  );
}
