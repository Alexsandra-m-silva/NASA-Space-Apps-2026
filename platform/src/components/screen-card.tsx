import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { FlowStep, PersonaId } from "@/data/types";

export function ScreenCard({
  personaId,
  step,
  stepIndex,
  total,
  prevId,
  nextId,
}: {
  personaId: PersonaId;
  step: FlowStep;
  stepIndex: number;
  total: number;
  prevId?: string;
  nextId?: string;
}) {
  return (
    <article className="animate-rise overflow-hidden rounded-md border border-border bg-card shadow-sm">
      <div className="border-b border-border bg-olive px-5 py-4 text-primary-foreground sm:px-7">
        <p className="text-[0.7rem] uppercase tracking-[0.18em] text-sand">
          Screen {stepIndex + 1} of {total} · {step.phase}
        </p>
        <h1 className="mt-1 font-display text-2xl sm:text-3xl">{step.title}</h1>
      </div>

      <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6 p-5 sm:p-7">
          <section>
            <h2 className="text-xs uppercase tracking-[0.16em] text-signal">
              Objective
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground sm:text-base">
              {step.objective}
            </p>
          </section>

          <section>
            <h2 className="text-xs uppercase tracking-[0.16em] text-signal">
              On-screen data
            </h2>
            <ul className="mt-2 space-y-2">
              {step.dataOnScreen.map((item) => (
                <li
                  key={item}
                  className="flex gap-2 text-sm leading-relaxed text-muted-foreground"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-earth" />
                  {item}
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-md border border-dashed border-border bg-muted/40 p-4">
            <h2 className="text-xs uppercase tracking-[0.16em] text-earth">
              User decision
            </h2>
            <p className="mt-2 text-sm font-medium leading-relaxed text-olive">
              {step.decision}
            </p>
          </section>

          <section>
            <h2 className="text-xs uppercase tracking-[0.16em] text-signal">
              CTA
            </h2>
            <p className="mt-2 inline-flex rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground">
              {step.cta}
            </p>
            <p className="mt-3 text-sm text-muted-foreground">{step.nextHint}</p>
          </section>
        </div>

        <aside className="border-t border-border bg-secondary/40 p-5 sm:p-7 lg:border-l lg:border-t-0">
          <p className="text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
            UI sketch (mock)
          </p>
          <div className="mt-3 rounded-md border border-border bg-card p-4 shadow-sm">
            <h3 className="font-display text-lg leading-snug text-olive">
              {step.sampleUi.headline}
            </h3>
            {step.sampleUi.metrics && (
              <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {step.sampleUi.metrics.map((m) => (
                  <div
                    key={m.label}
                    className="rounded-md border border-border/80 bg-signal-soft/50 px-3 py-2"
                  >
                    <dt className="text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
                      {m.label}
                    </dt>
                    <dd className="mt-1 font-display text-lg text-primary">
                      {m.value}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            {step.sampleUi.bullets && (
              <ul className="mt-4 space-y-2">
                {step.sampleUi.bullets.map((b) => (
                  <li key={b} className="text-sm text-muted-foreground">
                    · {b}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-4 sm:px-7">
        <div className="flex gap-2">
          {prevId ? (
            <Button asChild variant="outline">
              <Link href={`/persona/${personaId}/step/${prevId}`}>Previous</Link>
            </Button>
          ) : (
            <Button asChild variant="outline">
              <Link href={`/persona/${personaId}`}>Back to persona</Link>
            </Button>
          )}
          {nextId ? (
            <Button asChild>
              <Link href={`/persona/${personaId}/step/${nextId}`}>Next step</Link>
            </Button>
          ) : (
            <Button asChild>
              <Link href="/compare">See same evidence → 4 outputs</Link>
            </Button>
          )}
        </div>
        <Link
          href={`/persona/${personaId}`}
          className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          Flow board
        </Link>
      </div>
    </article>
  );
}
