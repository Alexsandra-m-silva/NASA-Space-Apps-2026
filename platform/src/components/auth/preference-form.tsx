"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ALL_IMPACTS,
  ALL_RISKS,
  LENS_LABELS,
  type AlertPreferences,
} from "@/data/alerts";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  type GeoLevel,
  type ImpactType,
  type RankingLens,
  RISK_LABELS,
  type RiskLevel,
} from "@/data/explore/types";
import {
  geoOptionsForLevel,
  loadIbgeMunicipios,
  type GeoOption,
} from "@/data/geo";
import { Button } from "@/components/ui/button";

const LEVELS: GeoLevel[] = ["bioma", "regiao", "estado", "municipio"];
const LENSES = Object.keys(LENS_LABELS) as RankingLens[];

const LEVEL_NOUN: Record<GeoLevel, string> = {
  bioma: "biomes",
  regiao: "regions",
  estado: "states",
  municipio: "municipalities",
};

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
      onClick={onClick}
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

function sameSet(a: string[], b: string[]) {
  if (a.length !== b.length) return false;
  const set = new Set(a);
  return b.every((x) => set.has(x));
}

export function PreferenceForm({
  initial,
  submitLabel,
  onSubmit,
  onCancelAlerts,
  cancelLabel = "Cancel newsletter updates",
}: {
  initial: AlertPreferences;
  submitLabel: string;
  onSubmit: (prefs: AlertPreferences) => void;
  onCancelAlerts?: (prefs: AlertPreferences) => void;
  cancelLabel?: string;
}) {
  const [prefs, setPrefs] = useState<AlertPreferences>(initial);
  const [municipios, setMunicipios] = useState<GeoOption[]>([]);
  const [munLoading, setMunLoading] = useState(false);
  const [munQuery, setMunQuery] = useState("");
  const [munError, setMunError] = useState<string | null>(null);

  useEffect(() => {
    setPrefs(initial);
  }, [initial]);

  useEffect(() => {
    if (prefs.level !== "municipio") return;
    let cancelled = false;
    setMunLoading(true);
    setMunError(null);
    loadIbgeMunicipios()
      .then((list) => {
        if (!cancelled) setMunicipios(list);
      })
      .catch(() => {
        if (!cancelled) {
          setMunError("Could not load IBGE municipalities.");
        }
      })
      .finally(() => {
        if (!cancelled) setMunLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [prefs.level]);

  const staticOptions = useMemo(
    () => geoOptionsForLevel(prefs.level),
    [prefs.level]
  );

  const territoryKey =
    prefs.level === "bioma"
      ? "biomas"
      : prefs.level === "regiao"
        ? "regioes"
        : prefs.level === "estado"
          ? "estados"
          : "municipios";

  const selectedTerritoryIds = prefs[territoryKey] as string[];

  const munFiltered = useMemo(() => {
    const q = munQuery.trim().toLowerCase();
    const selected = new Set(prefs.municipios);
    let list = municipios;
    if (q) {
      list = list.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.id.includes(q) ||
          (m.hint ?? "").toLowerCase().includes(q)
      );
    }
    if (!q) {
      const picked = list.filter((m) => selected.has(m.id));
      const rest = list.filter((m) => !selected.has(m.id)).slice(0, 40);
      return [...picked, ...rest].slice(0, 60);
    }
    return list.slice(0, 60);
  }, [municipios, munQuery, prefs.municipios]);

  const territoryOptions: GeoOption[] =
    prefs.level === "municipio" ? munFiltered : staticOptions;

  function toggleList(
    key: keyof Pick<
      AlertPreferences,
      | "biomas"
      | "regioes"
      | "estados"
      | "municipios"
      | "impacts"
      | "lenses"
      | "risks"
    >,
    id: string
  ) {
    setPrefs((p) => {
      const list = p[key] as string[];
      const next = list.includes(id)
        ? list.filter((x) => x !== id)
        : [...list, id];
      return { ...p, [key]: next };
    });
  }

  function setLevel(level: GeoLevel) {
    setPrefs((p) => ({ ...p, level }));
    setMunQuery("");
  }

  const impactsAll = sameSet(prefs.impacts, ALL_IMPACTS);
  const risksAll = sameSet(prefs.risks, ALL_RISKS);

  const selectedCount = selectedTerritoryIds.length;
  const levelNoun = LEVEL_NOUN[prefs.level];

  return (
    <form
      className="space-y-8"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ ...prefs, alertsEnabled: true });
      }}
    >
      {!prefs.alertsEnabled && (
        <p className="rounded-md border border-earth/30 bg-[#fff7ed] px-4 py-3 text-sm text-olive">
          Newsletter updates are turned off. Save preferences to reactivate.
        </p>
      )}

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
                active={prefs.level === l}
                onClick={() => setLevel(l)}
              />
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Select the {levelNoun} you want to monitor (multi-select). The level
            above is exclusive.
          </p>

          {prefs.level === "municipio" && (
            <div className="mt-3">
              <input
                type="search"
                value={munQuery}
                onChange={(e) => setMunQuery(e.target.value)}
                placeholder="Search municipality (name, state, or IBGE code)"
                className="h-10 w-full max-w-md rounded-md border border-input bg-background px-3 text-sm"
              />
              {munLoading && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Loading IBGE municipalities…
                </p>
              )}
              {munError && (
                <p className="mt-2 text-xs text-destructive">{munError}</p>
              )}
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {territoryOptions.map((o) => (
              <ChipToggle
                key={o.id}
                label={o.hint ? `${o.name} (${o.hint})` : o.name}
                active={selectedTerritoryIds.includes(o.id)}
                onClick={() => toggleList(territoryKey, o.id)}
              />
            ))}
            {prefs.level === "municipio" &&
              !munLoading &&
              territoryOptions.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No municipality found for that search.
                </p>
              )}
          </div>
          <p className="mt-2 text-[0.65rem] text-muted-foreground">
            Biomes: official IBGE/MMA classification. Regions, states, and
            municipalities: IBGE codes.
          </p>
        </fieldset>

        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Impact type
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            <ChipToggle
              label="All"
              active={impactsAll}
              onClick={() =>
                setPrefs((p) => ({
                  ...p,
                  impacts: impactsAll ? [] : [...ALL_IMPACTS],
                }))
              }
            />
            {ALL_IMPACTS.map((k) => (
              <ChipToggle
                key={k}
                label={IMPACT_LABELS[k]}
                active={!impactsAll && prefs.impacts.includes(k)}
                onClick={() => {
                  setPrefs((p) => {
                    const base = impactsAll ? [] : p.impacts;
                    const next = base.includes(k)
                      ? base.filter((x) => x !== k)
                      : [...base, k];
                    return { ...p, impacts: next as ImpactType[] };
                  });
                }}
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
              active={risksAll}
              onClick={() =>
                setPrefs((p) => ({
                  ...p,
                  risks: risksAll ? [] : [...ALL_RISKS],
                }))
              }
            />
            {ALL_RISKS.map((k) => (
              <ChipToggle
                key={k}
                label={RISK_LABELS[k]}
                active={!risksAll && prefs.risks.includes(k)}
                onClick={() => {
                  setPrefs((p) => {
                    const base = risksAll ? [] : p.risks;
                    const next = base.includes(k)
                      ? base.filter((x) => x !== k)
                      : [...base, k];
                    return { ...p, risks: next as RiskLevel[] };
                  });
                }}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Chart ranking (interest)
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            {LENSES.map((id) => (
              <ChipToggle
                key={id}
                label={LENS_LABELS[id]}
                active={prefs.lenses.includes(id)}
                onClick={() => toggleList("lenses", id)}
              />
            ))}
          </div>
        </fieldset>
      </div>

      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          checked={prefs.emailMonthly}
          onChange={(e) =>
            setPrefs((p) => ({ ...p, emailMonthly: e.target.checked }))
          }
          className="mt-1"
        />
        <span>Include a monthly digest even without a one-off trigger</span>
      </label>

      <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">
          {selectedCount} {levelNoun} ·{" "}
          {impactsAll
            ? "all impacts"
            : `${prefs.impacts.length} impact${prefs.impacts.length === 1 ? "" : "s"}`}{" "}
          ·{" "}
          {risksAll
            ? "all risks"
            : `${prefs.risks.length} risk${prefs.risks.length === 1 ? "" : "s"}`}{" "}
          · {prefs.lenses.length} lens{prefs.lenses.length === 1 ? "" : "es"}
        </p>
        <div className="flex flex-wrap gap-2">
          {onCancelAlerts && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const next = { ...prefs, alertsEnabled: false };
                setPrefs(next);
                onCancelAlerts(next);
              }}
            >
              {cancelLabel}
            </Button>
          )}
          <Button type="submit" variant="outline">
            {submitLabel}
          </Button>
        </div>
      </div>
    </form>
  );
}
