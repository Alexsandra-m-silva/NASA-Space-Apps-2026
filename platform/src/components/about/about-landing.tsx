import Link from "next/link";
import { AboutTeam } from "@/components/about/about-team";
import { HeroVideo } from "@/components/about/hero-video";
import { PartnerCta } from "@/components/about/partner-cta";
import { Button } from "@/components/ui/button";
import { brand } from "@/data/brand";

const AUDIENCE = [
  {
    who: "Public sector",
    what: "Governors, mayors, secretaries, and advisors who need numbers and actions to justify budgets, amendments, and municipal plans.",
  },
  {
    who: "Press and civil society",
    what: "Journalists and NGOs who need a stable story with methodology, limits, and a link that does not expire with the news cycle.",
  },
  {
    who: "Partner companies",
    what: "Teams restoring priority land who need territory-level proof, ranked credit potential, and a credible path from hectares restored to reportable climate value.",
  },
  {
    who: "Remote monitors",
    what: "Anyone who needs an email when trend, risk, or impact changes in the territory they already chose.",
  },
];

const TECH = [
  {
    title: "NISAR radar",
    body: "NASA–ISRO Synthetic Aperture Radar as the reference for surface change — including dry-season signals that optical imagery often misses.",
  },
  {
    title: "Risk and impact layers",
    body: "Trend becomes severity, then human and ecological impact: water stress, food security, income, migration, biodiversity pressure.",
  },
  {
    title: "Cost and credits",
    body: "Each selection carries the cost of waiting, the cost to prevent, and restoration carbon potential converted to an expected USD figure.",
  },
];

export function AboutLanding() {
  return (
    <div>
      {/* Hero — full-bleed video under copy/CTAs */}
      <section
        data-header-contrast="dark"
        className="relative -mt-[3.75rem] min-h-[88vh] overflow-hidden border-b border-border bg-[#220F08] pt-[3.75rem]"
      >
        <div aria-hidden className="absolute inset-0">
          <HeroVideo src="/hero/about-hero.mp4" className="h-full w-full object-cover" />
          {/* Gradient mask (benchmark: Hefesto hero): darker at the top for the header and at the bottom for the copy */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "linear-gradient(to bottom, rgba(34,15,8,.78) 0%, rgba(34,15,8,.35) 18%, rgba(34,15,8,.15) 45%, rgba(34,15,8,.85) 100%)",
            }}
          />
        </div>

        <div className="relative z-10 mx-auto flex min-h-[88vh] max-w-6xl flex-col justify-end px-4 pb-16 pt-28 sm:px-6 sm:pb-20">
          <p className="animate-rise font-display text-5xl leading-none tracking-tight text-[#FBF7EF] sm:text-6xl md:text-7xl lg:text-8xl">
            {brand.name}
          </p>
          <p className="animate-rise-delay-1 mt-5 max-w-xl text-lg leading-relaxed text-[#F3EBD9]">
            {brand.tagline}
          </p>
          <div className="animate-rise-delay-2 mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg" variant="accent">
              <Link href="/explore">Explore the evidence</Link>
            </Button>
            <Button asChild size="lg" variant="accent">
              <Link href="/newsletter">Get the newsletter</Link>
            </Button>
            <Button asChild size="lg" variant="accent">
              <Link href="/about#partners">Become a partner</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Objective */}
      <section
        data-header-contrast="light"
        className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20"
      >
        <p className="text-[0.7rem] uppercase tracking-[0.2em] text-signal">
          About the project
        </p>
        <h2 className="mt-2 font-display text-3xl text-olive sm:text-4xl">
          Objective
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-foreground sm:text-lg">
          {brand.purpose}
        </p>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
          {brand.thesis}
        </p>
      </section>

      {/* How it works — mid-dark band */}
      <section
        data-header-contrast="dark"
        className="border-y border-[#341C10] bg-[#642F07]"
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <h2 className="font-display text-3xl text-[#FBF7EF] sm:text-4xl">
            From signal to decision
          </h2>
          <p className="mt-3 max-w-2xl text-sm text-[#F3EBD9]">
            Three moves on the same evidence — see the trend, price the wait,
            restore with incentive.
          </p>
          <ol className="mt-10 grid gap-10 md:grid-cols-3">
            {[
              {
                n: "01",
                title: "See the trend",
                body: "Maps and rankings by surface trend, risk, and impact type — from biome to municipality.",
              },
              {
                n: "02",
                title: "Price the wait",
                body: "The cost of inaction sits next to each selection: expected loss versus the cost to prevent.",
              },
              {
                n: "03",
                title: "Restore with incentive",
                body: "Priority areas show carbon-credit potential in dollars for partners who regenerate — and, over time, protect.",
              },
            ].map((item) => (
              <div key={item.n}>
                <p className="font-display text-sm text-[#FFEA7F]">{item.n}</p>
                <h3 className="mt-2 font-display text-xl text-[#FBF7EF]">
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-[#DDD5BA]">
                  {item.body}
                </p>
              </div>
            ))}
          </ol>
        </div>
      </section>

      {/* Audience */}
      <section
        data-header-contrast="light"
        className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20"
      >
        <h2 className="font-display text-3xl text-olive sm:text-4xl">
          Who it is for
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
          Same evidence, different outputs — from a budget annex to a reporting
          kit and a regeneration pipeline.
        </p>
        <ul className="mt-8 grid gap-6 sm:grid-cols-2">
          {AUDIENCE.map((row) => (
            <li key={row.who} className="border-l-2 border-signal pl-4">
              <h3 className="font-display text-lg text-olive">{row.who}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {row.what}
              </p>
            </li>
          ))}
        </ul>
      </section>

      {/* Technology — mid-dark band */}
      <section
        data-header-contrast="dark"
        className="border-y border-[#341C10] bg-[#642F07]"
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <h2 className="font-display text-3xl text-[#FBF7EF] sm:text-4xl">
            Technology
          </h2>
          <p className="mt-3 max-w-2xl text-sm text-[#F3EBD9]">
            Built for the NASA Space Apps Challenge — grounded in Earth
            observation, open enough for cabinets and newsrooms to trust the
            limits of the prototype.
          </p>
          <div className="mt-10 grid gap-10 md:grid-cols-3">
            {TECH.map((item) => (
              <div key={item.title}>
                <h3 className="font-display text-xl text-[#FBF7EF]">
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-[#DDD5BA]">
                  {item.body}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-10 max-w-3xl text-xs leading-relaxed text-[#DDD5BA]">
            Sample data in this build. Satellite-derived degradation is not the
            same as field-proven desertification. Carbon figures use a
            prototype market reference and are not a certified methodology.
          </p>
        </div>
      </section>

      {/* Product surfaces */}
      <section
        data-header-contrast="light"
        className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20"
      >
        <h2 className="font-display text-3xl text-olive sm:text-4xl">
          What you can do here
        </h2>
        <div className="mt-8 grid gap-8 sm:grid-cols-2">
          <div>
            <h3 className="font-display text-xl text-olive">Explore</h3>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Filter by territory, impact, and risk. Read the spotlight, map,
              suggested actions, and rankings — then carry your selection into
              the newsletter.
            </p>
          </div>
          <div>
            <h3 className="font-display text-xl text-olive">Newsletter</h3>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Set institutional contact, role, and monitoring criteria. You are
              notified only when the evidence in your selection actually
              changes.
            </p>
          </div>
        </div>
      </section>

      <AboutTeam />

      {/* Partners — companies only; soft Mel wash for quiet highlight */}
      <section
        id="partners"
        data-header-contrast="light"
        className="scroll-mt-24 border-y border-[#E5D4A8] bg-[#F3EBD9] px-4 py-10 sm:px-6"
      >
        <div className="mx-auto max-w-6xl rounded-md border border-[#E0D0A0] bg-[#FAF4E4] px-5 py-6 shadow-sm sm:px-7 sm:py-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div className="max-w-xl">
              <p className="text-[0.7rem] uppercase tracking-[0.2em] text-signal">
                For companies
              </p>
              <h2 className="mt-2 font-display text-2xl text-olive sm:text-3xl">
                Turn restoration into measurable climate value
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Companies that regenerate priority land get territory-level
                evidence — trend, risk, impact, and recoverable area — plus an
                estimate of carbon-credit potential in dollars. Use it to
                prioritize where to invest, report progress with the same map
                decision-makers see, and build a credible path from hectares
                restored to credits. Leave interest here for a company track:
                priority territories, cost of inaction vs. prevention, and
                modeled credit upside — separate from the public newsletter.
              </p>
            </div>
            <PartnerCta />
          </div>
        </div>
      </section>

      {/* Closing CTA */}
      <section
        data-header-contrast="dark"
        className="border-t border-border bg-olive text-primary-foreground"
      >
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-16 sm:flex-row sm:items-end sm:justify-between sm:px-6 sm:py-20">
          <div className="max-w-xl">
            <h2 className="font-display text-3xl text-[#FBF7EF] sm:text-4xl">
              Start with the map
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-[#F3EBD9]">
              Explore trend, risk, impact, and carbon — or set alerts when the
              ground truly changes.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="accent">
              <Link href="/explore">Explore</Link>
            </Button>
            <Button asChild variant="accent">
              <Link href="/newsletter">Subscribe to the newsletter</Link>
            </Button>
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-muted-foreground sm:px-6">
        <p>
          {brand.name} · NASA Space Apps Challenge · CLIMA / Terra e luz ·
          sample data in this prototype · NISAR as the reference for surface
          trend
        </p>
      </footer>
    </div>
  );
}
