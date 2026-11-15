"use client";

import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { plural } from "@/lib/utils";
import {
  formatCredits,
  formatTransitionRisk,
  aggregateCost,
} from "@/data/explore/queries";
import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  RISK_LABELS,
  type GeoLevel,
  type ImpactType,
  type RiskLevel,
  type Territory,
} from "@/data/explore/types";
import { buildActionSuggestions } from "@/data/explore/actions";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

/** Inline **bold** → <strong>. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    )
  );
}

/** Minimal Markdown for chat answers: paragraphs, "-"/"*"/"1." lists, headings, bold. */
function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (!list) return;
    const Tag = list.ordered ? "ol" : "ul";
    blocks.push(
      <Tag
        key={`l${blocks.length}`}
        className={list.ordered ? "ml-4 list-decimal space-y-0.5" : "ml-4 list-disc space-y-0.5"}
      >
        {list.items.map((it, i) => (
          <li key={i}>{inline(it)}</li>
        ))}
      </Tag>
    );
    list = null;
  };
  for (const raw of text.replace(/\r/g, "").split("\n")) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    const ul = line.match(/^[-*•]\s+(.*)$/);
    const ol = line.match(/^\d+[.)]\s+(.*)$/);
    if (ul || ol) {
      const ordered = !!ol;
      if (!list || list.ordered !== ordered) {
        flush();
        list = { ordered, items: [] };
      }
      list.items.push((ul ?? ol)![1]);
      continue;
    }
    flush();
    const h = line.match(/^#{1,4}\s+(.*)$/);
    blocks.push(
      <p key={`p${blocks.length}`} className={h ? "font-semibold" : undefined}>
        {inline(h ? h[1] : line)}
      </p>
    );
  }
  flush();
  return <div className="space-y-1.5">{blocks}</div>;
}

const SUGGESTIONS = [
  "What should we prioritize here?",
  "Summarize the risk in this view",
  "Which impact is most critical?",
  "Where are carbon credits strongest?",
];

function replyFor(
  question: string,
  ctx: {
    items: Territory[];
    level: GeoLevel;
    impact: ImpactType | "todos";
    risk: RiskLevel | "todos";
  }
): string {
  const q = question.toLowerCase();
  const costs = aggregateCost(ctx.items);
  const actions = buildActionSuggestions(ctx);
  const n = ctx.items.length;
  const level = LEVEL_LABELS[ctx.level].toLowerCase();
  const impactLabel =
    ctx.impact === "todos" ? "all impact types" : IMPACT_LABELS[ctx.impact];
  const riskLabel =
    ctx.risk === "todos" ? "all risk levels" : RISK_LABELS[ctx.risk];

  const top = [...ctx.items]
    .sort((a, b) => b.creditosCarbonoTco2e - a.creditosCarbonoTco2e)
    .slice(0, 3);

  if (!n) {
    return "No territories match the current filters. Widen impact, risk, or search to get a grounded answer.";
  }

  if (q.includes("carbon") || q.includes("credit")) {
    const names = top.map((t) => t.name).join(", ");
    return `In this ${level} view (${n} territories · ${impactLabel} · ${riskLabel}), estimated restoration credits total ${formatCredits(costs.creditos)} across ${Math.round(costs.areaHa).toLocaleString("en-US")} ha. Strongest credit potential: ${names}.`;
  }

  if (q.includes("impact") || q.includes("critical")) {
    const counts = new Map<ImpactType, number>();
    for (const t of ctx.items) {
      for (const i of t.impacts) counts.set(i, (counts.get(i) ?? 0) + 1);
    }
    const ranked = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const lead = ranked[0];
    if (!lead) {
      return "Impact tags are empty for this selection.";
    }
    return `Most frequent impact here is ${IMPACT_LABELS[lead[0]]} (${lead[1]} of ${n} ${plural(level)}). Filter Impact type to isolate it, then check “What to do now” for preserve / slow / reverse moves.`;
  }

  if (q.includes("risk") || q.includes("summar")) {
    const critico = ctx.items.filter((t) => t.risk === "critico").length;
    const alto = ctx.items.filter((t) => t.risk === "alto").length;
    return `Selection: ${n} ${plural(level)} · ${impactLabel} · ${riskLabel}. Transition risk index ${formatTransitionRisk(costs.transitionRisk)} (SDG 13). Critical: ${critico} · High: ${alto}. Use the map to pick a territory, then ask what to prioritize.`;
  }

  const first = actions[0];
  if (q.includes("priorit") || q.includes("should") || q.includes("do now") || first) {
    if (!first) {
      return `I see ${n} ${plural(level)} but no strong action cards yet. Try raising risk severity or focusing one impact type.`;
    }
    return `I’d prioritize “${first.title}” (${first.kind}). ${first.summary} Why: ${first.why}`;
  }

  return `This view covers ${n} ${plural(level)} (${impactLabel}, ${riskLabel}). Transition risk ${formatTransitionRisk(costs.transitionRisk)}; credit potential ${formatCredits(costs.creditos)}. Ask about priorities, risk, impacts, or carbon — answers stay tied to the filters you set.`;
}

export function ExploreChat({
  items,
  level,
  impact,
  risk,
  variant = "panel",
}: {
  items: Territory[];
  level: GeoLevel;
  impact: ImpactType | "todos";
  risk: RiskLevel | "todos";
  variant?: "panel" | "overlay";
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Ask about this map view — priorities, risk, impacts, or carbon. Answers use the filters you already applied.",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasAsked = messages.some((m) => m.role === "user");

  // Keep the latest message (and the typing indicator) in view
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  const impactLabel =
    impact === "todos" ? "all impacts" : IMPACT_LABELS[impact];
  const riskLabel = risk === "todos" ? "all risks" : RISK_LABELS[risk];
  const isOverlay = variant === "overlay";

  function send(text: string) {
    const cleaned = text.trim();
    if (!cleaned || pending) return;
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text: cleaned,
    };
    setMessages((m) => [...m, userMsg]);
    setDraft("");
    setPending(true);
    const history = messages
      .filter((m) => m.id !== "welcome")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.text }));
    const screenContext = JSON.stringify({
      view: `Desert Sentinel explore · ${LEVEL_LABELS[level]} · ${impactLabel} · ${riskLabel}`,
      territories: items.slice(0, 25).map((t) => ({
        name: t.name, level: t.level, risk: RISK_LABELS[t.risk] ?? t.risk, trend_pct_area_declining: t.tendenciaPp,
        impacts: t.impacts, disaster_losses_2015_24_brl_mi: t.custoNaoAgirMi,
        restore_cost_estimate_brl_mi: t.custoPrevenirMi, population_2022: t.populacaoEstimada,
        degraded_ha: t.areaRecuperavelHa, carbon_estimate_tco2e: t.creditosCarbonoTco2e, evidence: t.dados,
      })),
    }).slice(0, 15000);
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: cleaned, screen_context: screenContext, history }),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(String(r.status));
        const data = (await r.json()) as { answer?: string };
        if (!data.answer) throw new Error("empty");
        return data.answer;
      })
      .catch(() => replyFor(cleaned, { items, level, impact, risk }))
      .then((answer) => {
        setMessages((m) => [
          ...m,
          { id: `a-${Date.now()}`, role: "assistant", text: answer },
        ]);
        setPending(false);
      });
  }

  return (
    <div
      className={
        isOverlay
          ? "flex h-full min-h-0 flex-col bg-transparent p-3 sm:p-4"
          : "flex h-full min-h-[320px] flex-col rounded-md border border-border bg-card p-3 shadow-sm sm:min-h-[420px] sm:p-4"
      }
    >
      <div className="mb-3 shrink-0">
        {!isOverlay && (
          <>
            <p className="text-[0.65rem] uppercase tracking-[0.16em] text-signal">
              Desert Sentinel
            </p>
            <h2 className="mt-1 font-display text-base text-olive sm:text-lg">
              Ask the evidence
            </h2>
          </>
        )}
        <p
          className={
            isOverlay
              ? "text-xs leading-relaxed text-muted-foreground"
              : "mt-1 text-[0.7rem] leading-relaxed text-muted-foreground sm:text-xs"
          }
        >
          Local briefing over the current selection — not a general chatbot.
        </p>
        <p className="mt-2 text-[0.65rem] text-muted-foreground">
          {items.length} {plural(LEVEL_LABELS[level].toLowerCase())} · {impactLabel} ·{" "}
          {riskLabel}
        </p>
      </div>

      <div
        ref={scrollRef}
        aria-live="polite"
        className="min-h-0 flex-1 space-y-2.5 overflow-y-auto overscroll-contain pr-0.5"
      >
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-md px-3 py-2 text-sm leading-relaxed ${
              m.role === "user"
                ? "ml-6 bg-primary text-primary-foreground"
                : "mr-4 border border-border bg-background/90 text-foreground"
            }`}
          >
            {m.role === "assistant" ? <RichText text={m.text} /> : m.text}
          </div>
        ))}
        {pending && (
          <div
            className="mr-4 flex items-center gap-2 rounded-md border border-border bg-background/90 px-3 py-2 text-xs text-muted-foreground"
            role="status"
          >
            <span className="flex gap-1" aria-hidden>
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
            </span>
            Sentinel is reading the selection…
          </div>
        )}
      </div>

      <div className="mt-3 shrink-0 space-y-2 border-t border-border pt-3">
        <div className={hasAsked ? "hidden" : "flex flex-wrap gap-1.5"}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => send(s)}
              className="rounded-md border border-border bg-background px-2 py-1 text-[0.65rem] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
            >
              {s}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about this map view…"
            className="h-10 min-w-0 flex-1 rounded-md border border-input bg-background px-3 text-sm"
            aria-label="Message"
            disabled={pending}
          />
          <Button type="submit" variant="outline" disabled={pending}>
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
