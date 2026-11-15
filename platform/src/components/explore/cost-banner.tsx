import {
  CARBON_CREDIT_USD_PER_TCO2E,
  formatCarbonUsd,
  formatCredits,
  formatHectares,
  formatTransitionRisk,
} from "@/data/explore/queries";

export function CostBanner({
  creditos,
  areaHa,
  transitionRisk,
}: {
  creditos: number;
  areaHa: number;
  transitionRisk: number;
  count?: number;
  levelLabel?: string;
}) {
  return (
    <aside
      data-header-contrast="dark"
      className="animate-rise overflow-hidden rounded-md border border-primary/40 bg-olive text-primary-foreground shadow-sm"
      aria-live="polite"
    >
      <div className="border-b border-white/10 px-5 py-3 sm:px-6">
        <p className="text-[0.7rem] uppercase tracking-[0.2em] text-accent">
          Spotlight
        </p>
      </div>

      <div className="grid gap-0 md:grid-cols-2">
        <div className="px-5 py-5 sm:px-6 md:border-r md:border-white/10">
          <p className="text-[0.7rem] uppercase tracking-[0.16em] text-sand/80">
            Transition risk · SDG 13
          </p>
          <p className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
            {formatTransitionRisk(transitionRisk)}
          </p>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-sand">
            Measures how exposed the territory is to losses and costs if climate
            and land use keep changing — aligned with UN SDG 13 (climate action).
            A higher score means greater urgency to act.
          </p>
        </div>

        <div className="border-t border-white/10 px-5 py-5 md:border-t-0 sm:px-6">
          <p className="text-[0.7rem] uppercase tracking-[0.16em] text-sand/80">
            Carbon credits if the area is restored
          </p>
          <div className="mt-2 grid gap-4 sm:grid-cols-2 sm:gap-6">
            <div>
              <p className="font-display text-3xl tracking-tight text-accent sm:text-4xl">
                {formatCredits(creditos)}
              </p>
              <p className="mt-1 text-[0.65rem] uppercase tracking-[0.12em] text-sand/65">
                Estimated credits
              </p>
            </div>
            <div>
              <p className="font-display text-3xl tracking-tight text-accent sm:text-4xl">
                {formatCarbonUsd(creditos)}
              </p>
              <p className="mt-1 text-[0.65rem] uppercase tracking-[0.12em] text-sand/65">
                Expected financial impact
              </p>
            </div>
          </div>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-sand">
            Estimated potential across {formatHectares(areaHa)} eligible (1
            credit ≈ 1 tCO₂e × ${CARBON_CREDIT_USD_PER_TCO2E}/tCO₂e prototype
            market reference — sample, not certified methodology).
          </p>
        </div>
      </div>
    </aside>
  );
}
