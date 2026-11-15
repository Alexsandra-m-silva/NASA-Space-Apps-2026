import { Badge } from "@/components/ui/badge";
import {
  formatBRLMillions,
  formatCredits,
  formatHectares,
  formatTrend,
} from "@/data/explore/queries";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  REGEN_LABELS,
  RISK_LABELS,
  type Territory,
} from "@/data/explore/types";

export function TerritoryDetail({ territory }: { territory: Territory | null }) {
  if (!territory) return null;

  return (
    <article className="animate-rise rounded-md border border-border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{LEVEL_LABELS[territory.level]}</Badge>
        <Badge
          className={
            territory.risk === "critico"
              ? "bg-destructive text-destructive-foreground"
              : territory.risk === "alto"
                ? "bg-earth text-primary-foreground"
                : "bg-accent text-accent-foreground"
          }
        >
          {RISK_LABELS[territory.risk]}
        </Badge>
        <Badge variant="secondary">
          {REGEN_LABELS[territory.regeneracaoStatus]}
        </Badge>
      </div>
      <h3 className="mt-2 font-display text-2xl text-olive">{territory.name}</h3>

      <div className="mt-4 rounded-md border border-signal/30 bg-signal-soft/70 px-4 py-3">
        <p className="text-[0.65rem] uppercase tracking-[0.14em] text-signal">
          Restore → potential credits
        </p>
        <p className="mt-1 font-display text-2xl text-primary">
          {formatCredits(territory.creditosCarbonoTco2e)}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Across {formatHectares(territory.areaRecuperavelHa)} eligible · sample
          (1 credit ≈ 1 tCO₂e)
        </p>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-md bg-secondary/70 px-3 py-2">
          <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
            Trend
          </dt>
          <dd className="font-display text-lg text-primary">
            {formatTrend(territory.tendenciaPp)}
          </dd>
        </div>
        <div className="rounded-md bg-secondary/70 px-3 py-2">
          <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
            Population (est.)
          </dt>
          <dd className="font-display text-lg text-olive">
            {territory.populacaoEstimada.toLocaleString("en-US")}
          </dd>
        </div>
        <div className="rounded-md border border-border px-3 py-2">
          <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
            Inaction (10 yr)
          </dt>
          <dd className="font-display text-lg">
            {formatBRLMillions(territory.custoNaoAgirMi)}
          </dd>
        </div>
        <div className="rounded-md border border-border px-3 py-2">
          <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
            Prevent
          </dt>
          <dd className="font-display text-lg text-signal">
            {formatBRLMillions(territory.custoPrevenirMi)}
          </dd>
        </div>
      </dl>

      <div className="mt-4">
        <h4 className="text-xs uppercase tracking-[0.14em] text-signal">
          Impact types
        </h4>
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {territory.impacts.map((i) => (
            <li
              key={i}
              className="rounded-sm bg-secondary px-2 py-1 text-xs text-secondary-foreground"
            >
              {IMPACT_LABELS[i]}
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
