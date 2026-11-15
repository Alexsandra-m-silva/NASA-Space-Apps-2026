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
          Estimate · {formatHectares(territory.areaRecuperavelHa)} of degraded land × 53.9 tCO₂e/ha soil carbon
          (Bieluczyk et al.) · 1 credit ≈ 1 tCO₂e
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
            Population (2022)
          </dt>
          <dd className="font-display text-lg text-olive">
            {territory.populacaoEstimada.toLocaleString("en-US")}
          </dd>
        </div>
        <div className="rounded-md border border-border px-3 py-2">
          <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
            Disaster losses 2015–24
          </dt>
          <dd className="font-display text-lg">
            {formatBRLMillions(territory.custoNaoAgirMi)}
          </dd>
        </div>
        <div className="rounded-md border border-border px-3 py-2">
          <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
            Restore (estimate)
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

      {territory.dados && <Evidence territory={territory} />}
    </article>
  );
}

function Evidence({ territory }: { territory: Territory }) {
  const d = territory.dados ?? {};
  const rows: [string, string][] = [];
  if (d.area_estudo) rows.push(["Study area", d.area_estudo]);
  if (d.pct_melhora !== undefined) rows.push(["Improving vegetation (MODIS)", `${d.pct_melhora.toFixed(1)}% of the area`]);
  if (d.nisar) {
    rows.push(["NISAR degradation probability", `${Math.round(d.nisar.prob_media * 100)}% (mean of ${d.nisar.pontos} points)`]);
    if (d.nisar.auc !== null) rows.push(["NISAR confirms MODIS (AUC)", d.nisar.auc.toFixed(2)]);
  }
  if (d.aquecimento_c_decada !== undefined)
    rows.push(["Warming 1991–2024", `${d.aquecimento_c_decada > 0 ? "+" : ""}${d.aquecimento_c_decada.toFixed(2)} °C/decade${d.aquecimento_significativo ? " (significant)" : ""}`]);
  if (d.chuva_1991_2007_mm !== undefined && d.chuva_2008_2024_mm !== undefined)
    rows.push(["Rainfall 1991–2007 → 2008–24", `${d.chuva_1991_2007_mm} → ${d.chuva_2008_2024_mm} mm/yr`]);
  if (d.suscetibilidade_indice) rows.push(["Susceptibility index", d.suscetibilidade_indice.toFixed(2)]);
  if (d.emergencias_reconhecidas_10a !== undefined) rows.push(["Recognised emergencies 2015–24", String(d.emergencias_reconhecidas_10a)]);
  if (d.desmatamento_ha_2001_2024) rows.push(["Native vegetation cleared 2001–24", formatHectares(d.desmatamento_ha_2001_2024)]);
  if (d.nota) rows.push(["Note", d.nota]);
  if (!rows.length) return null;
  return (
    <div className="mt-4">
      <h4 className="text-xs uppercase tracking-[0.14em] text-signal">Evidence</h4>
      <dl className="mt-2 space-y-1 text-xs">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-border/60 py-1">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="text-right text-foreground">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[0.65rem] leading-relaxed text-muted-foreground">
        Sources: MODIS 2001–2024 with rainfall removed, NASA NISAR (provisional, 2026 dry season), CHIRPS, ERA5-Land,
        MapBiomas, Atlas Digital de Desastres (S2iD), IBGE 2022. Restore cost and carbon are estimates (TNC 2018; Bieluczyk et al.).
      </p>
    </div>
  );
}
