import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Persona } from "@/data/types";

const accentBorder: Record<string, string> = {
  gestor: "border-l-signal",
  prefeito: "border-l-earth",
  assessor: "border-l-accent",
  jornalista: "border-l-olive",
  familia: "border-l-muted-foreground",
};

export function PersonaCard({
  persona,
  delayClass = "",
}: {
  persona: Persona;
  delayClass?: string;
}) {
  const isStretch = persona.priority === "stretch";

  return (
    <Link
      href={`/persona/${persona.id}`}
      className={`group animate-rise block rounded-md border border-border border-l-4 bg-card/90 p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-md ${accentBorder[persona.accent] ?? "border-l-primary"} ${delayClass} ${isStretch ? "opacity-90" : ""}`}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge
          variant={isStretch ? "outline" : "default"}
          className={
            isStretch
              ? "border-earth/40 text-earth"
              : "bg-primary text-primary-foreground"
          }
        >
          {isStretch ? "Stretch" : "P0"}
        </Badge>
        <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          {persona.shortRole}
        </span>
      </div>
      <h3 className="font-display text-xl leading-tight text-olive transition-colors group-hover:text-primary">
        {persona.name}
      </h3>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        {persona.jobToBeDone}
      </p>
      <p className="mt-4 text-xs font-medium uppercase tracking-[0.12em] text-signal">
        Output → {persona.primaryOutput}
      </p>
    </Link>
  );
}
