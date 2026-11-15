"use client";

import { Badge } from "@/components/ui/badge";
import {
  formatBRLMillions,
  formatCredits,
  formatHectares,
  formatTrend,
} from "@/data/explore/queries";
import {
  IMPACT_LABELS,
  RISK_LABELS,
  type ImpactType,
  type RankingLens,
  type Territory,
} from "@/data/explore/types";

const riskBadge: Record<string, string> = {
  critico: "bg-destructive text-destructive-foreground border-transparent",
  alto: "bg-earth text-primary-foreground border-transparent",
  moderado: "bg-accent text-accent-foreground border-transparent",
};

export function RankingList({
  items,
  lens,
  selectedId,
  onSelect,
  impactFilter,
}: {
  items: Territory[];
  lens: RankingLens;
  selectedId: string | null;
  onSelect: (id: string) => void;
  impactFilter?: ImpactType | "todos";
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-card/70 p-8 text-center">
        <p className="font-display text-lg text-olive">No territories in this filter</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Broaden the geographic level or clear impact type / risk filters.
        </p>
      </div>
    );
  }

  return (
    <ol className="space-y-2">
      {items.map((t, index) => {
        const active = selectedId === t.id;
        return (
          <li key={t.id}>
            <button
              type="button"
              onClick={() => onSelect(t.id)}
              className={`flex w-full items-start gap-3 rounded-md border px-3 py-3 text-left transition-all ${
                active
                  ? "border-primary bg-signal-soft shadow-sm"
                  : "border-border bg-card/90 hover:border-primary/40 hover:shadow-sm"
              }`}
            >
              <span className="mt-0.5 w-6 shrink-0 font-display text-sm text-muted-foreground">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-display text-base text-olive">{t.name}</span>
                  <Badge className={riskBadge[t.risk]}>{RISK_LABELS[t.risk]}</Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  {lens === "carbono" ? (
                    <>
                      <span>
                        Credits{" "}
                        <strong className="text-signal">
                          {formatCredits(t.creditosCarbonoTco2e)}
                        </strong>
                      </span>
                      <span>
                        Area{" "}
                        <strong className="text-foreground">
                          {formatHectares(t.areaRecuperavelHa)}
                        </strong>
                      </span>
                    </>
                  ) : (
                    <>
                      <span>
                        Trend{" "}
                        <strong className="text-foreground">
                          {formatTrend(t.tendenciaPp)}
                        </strong>
                      </span>
                      <span>
                        Inaction{" "}
                        <strong className="text-foreground">
                          {formatBRLMillions(t.custoNaoAgirMi)}
                        </strong>
                      </span>
                      <span>
                        Carbon{" "}
                        <strong className="text-signal">
                          {formatCredits(t.creditosCarbonoTco2e)}
                        </strong>
                      </span>
                    </>
                  )}
                </div>
                {(lens === "impacto" ||
                  (impactFilter && impactFilter !== "todos")) && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {t.impacts.map((imp) => (
                      <span
                        key={imp}
                        className={`rounded-sm px-1.5 py-0.5 text-[0.65rem] ${
                          impactFilter === imp
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-secondary-foreground"
                        }`}
                      >
                        {IMPACT_LABELS[imp]}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}