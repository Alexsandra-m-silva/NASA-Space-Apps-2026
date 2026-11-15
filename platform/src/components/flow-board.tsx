import Link from "next/link";
import type { FlowStep, PersonaId } from "@/data/types";

export function FlowBoard({
  personaId,
  steps,
  activeStepId,
}: {
  personaId: PersonaId;
  steps: FlowStep[];
  activeStepId?: string;
}) {
  return (
    <div className="overflow-x-auto pb-2">
      <ol className="flex min-w-max gap-0 md:min-w-0 md:flex-wrap">
        {steps.map((step, index) => {
          const active = activeStepId === step.id;
          return (
            <li key={step.id} className="flex items-stretch">
              <Link
                href={`/persona/${personaId}/step/${step.id}`}
                className={`flex w-44 flex-col rounded-md border p-3 transition-all duration-200 sm:w-48 ${
                  active
                    ? "border-primary bg-signal-soft shadow-md"
                    : "border-border bg-card/80 hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-sm"
                }`}
              >
                <span className="text-[0.65rem] uppercase tracking-[0.16em] text-muted-foreground">
                  {String(index + 1).padStart(2, "0")} · {step.phase}
                </span>
                <span className="mt-2 font-display text-sm leading-snug text-olive">
                  {step.title}
                </span>
              </Link>
              {index < steps.length - 1 && (
                <div
                  aria-hidden
                  className="mx-1 flex w-4 items-center justify-center text-earth/70"
                >
                  →
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
