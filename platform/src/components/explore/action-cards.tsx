"use client";

import { useMemo } from "react";
import { plural } from "@/lib/utils";
import {
  ACTION_KIND_LABELS,
  buildActionSuggestions,
  type ActionKind,
} from "@/data/explore/actions";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  type GeoLevel,
  type ImpactType,
  type RiskLevel,
  type Territory,
} from "@/data/explore/types";

const kindStyles: Record<ActionKind, string> = {
  preservar: "border-signal/40 bg-signal-soft/50 text-signal",
  retardar: "border-earth/35 bg-[#fff7ed] text-earth",
  reverter: "border-primary/35 bg-primary/10 text-primary",
};

export function ActionCards({
  items,
  level,
  impact,
  risk,
}: {
  items: Territory[];
  level: GeoLevel;
  impact: ImpactType | "todos";
  risk: RiskLevel | "todos";
}) {
  const actions = useMemo(
    () => buildActionSuggestions({ items, level, impact, risk }),
    [items, level, impact, risk]
  );

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border border-border bg-card p-3 shadow-sm sm:p-4">
      <div className="mb-3">
        <p className="text-[0.65rem] uppercase tracking-[0.16em] text-signal">
          Exploration focus
        </p>
        <h2 className="mt-1 font-display text-base text-olive sm:text-lg">
          What to do now
        </h2>
        <p className="mt-1 text-[0.7rem] leading-relaxed text-muted-foreground sm:text-xs">
          Suggestions to{" "}
          <strong className="font-medium text-foreground">preserve</strong>,{" "}
          <strong className="font-medium text-foreground">slow</strong>, or{" "}
          <strong className="font-medium text-foreground">reverse</strong> impact
          in the current filtered view
          {impact !== "todos" ? ` · ${IMPACT_LABELS[impact]}` : ""} ·{" "}
          {plural(LEVEL_LABELS[level].toLowerCase())}.
        </p>
      </div>

      {actions.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Adjust filters to generate action suggestions for this view.
        </div>
      ) : (
        <ol className="flex flex-1 flex-col gap-2.5 overflow-y-auto pr-0.5">
          {actions.map((action, index) => (
            <li
              key={action.id}
              className="rounded-md border border-border bg-background/80 p-3 transition-colors hover:border-primary/30"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-display text-xs text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span
                  className={`rounded-sm border px-1.5 py-0.5 text-[0.65rem] font-medium uppercase tracking-[0.08em] ${kindStyles[action.kind]}`}
                >
                  {ACTION_KIND_LABELS[action.kind]}
                </span>
              </div>
              <h3 className="mt-2 font-display text-sm leading-snug text-olive sm:text-base">
                {action.title}
              </h3>
              <p className="mt-1.5 text-[0.75rem] leading-relaxed text-muted-foreground sm:text-xs">
                {action.summary}
              </p>
              <dl className="mt-2.5 grid grid-cols-1 gap-1.5 sm:grid-cols-3">
                {action.metrics.map((m) => (
                  <div
                    key={m.label}
                    className="rounded-sm bg-secondary/60 px-2 py-1.5"
                  >
                    <dt className="text-[0.6rem] uppercase tracking-[0.1em] text-muted-foreground">
                      {m.label}
                    </dt>
                    <dd className="mt-0.5 text-xs font-medium text-foreground">
                      {m.value}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-[0.65rem] leading-relaxed text-muted-foreground">
                {action.why}
              </p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
