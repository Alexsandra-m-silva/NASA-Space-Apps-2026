const TRIGGERS = [
  {
    title: "Trend shift",
    body: "A meaningful change in the surface index for your selection (≥ 5 p.p. or 10%) — material to refresh coverage or analysis.",
  },
  {
    title: "Risk category",
    body: "A change in severity (moderate, high, or critical) in the territory you follow.",
  },
  {
    title: "Impact type",
    body: "Impacts added or removed from monitoring — food security, water stress, income, migration, or biodiversity.",
  },
  {
    title: "New territory at risk",
    body: "A biome, region, state, or municipality enters the risk filter you configured.",
  },
];

export function EmailTriggersCard() {
  return (
    <aside className="rounded-md border border-signal/35 bg-signal-soft/60 p-5 shadow-sm sm:p-6">
      <p className="text-[0.65rem] uppercase tracking-[0.16em] text-signal">
        What triggers the email
      </p>
      <h2 className="mt-1 font-display text-xl text-olive">
        Newsletter criteria
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Messages go out only when the evidence changes in your selection — no
        noise, with context for press, government, and business.
      </p>
      <ul className="mt-5 grid gap-3 sm:grid-cols-2">
        {TRIGGERS.map((t) => (
          <li
            key={t.title}
            className="rounded-md border border-border/80 bg-card/90 px-3.5 py-3"
          >
            <p className="text-sm font-medium text-olive">{t.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {t.body}
            </p>
          </li>
        ))}
      </ul>
    </aside>
  );
}
