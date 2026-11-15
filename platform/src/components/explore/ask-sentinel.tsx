"use client";

import { useEffect, useId, useState } from "react";
import { ChevronDown } from "lucide-react";
import { AskSentinelMark } from "@/components/explore/ask-sentinel-mark";
import { ExploreChat } from "@/components/explore/explore-chat";
import { cn } from "@/lib/utils";
import type {
  GeoLevel,
  ImpactType,
  RiskLevel,
  Territory,
} from "@/data/explore/types";

/**
 * Help-desk style chat: a launcher in the bottom-right corner opens a drop-up
 * panel beside the content. Non-modal — no backdrop, no scroll lock — so the
 * map, filters and rankings stay usable while the chat is open.
 */
export function AskSentinel({
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
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="pointer-events-none fixed bottom-4 right-3 z-40 flex flex-col items-end gap-2 sm:bottom-6 sm:right-5">
      {/* Panel stays mounted so the conversation survives closing/reopening */}
      <section
        id={panelId}
        role="region"
        aria-labelledby={titleId}
        hidden={!open}
        className={cn(
          "pointer-events-auto flex w-[min(400px,calc(100vw-1.5rem))] flex-col overflow-hidden rounded-lg border border-border bg-card text-foreground shadow-2xl",
          "h-[min(560px,calc(100vh-10rem))]",
          !open && "hidden"
        )}
      >
        <header className="flex items-center justify-between gap-3 border-b border-border bg-[#220F08] px-4 py-3 text-[#FBF7EF]">
          <div className="flex min-w-0 items-center gap-2.5">
            <AskSentinelMark className="h-5 w-5 text-[#DAA849]" />
            <h2 id={titleId} className="truncate font-display text-base">
              Ask Sentinel
            </h2>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-md p-1.5 text-[#FBF7EF]/80 transition-colors hover:bg-white/10 hover:text-[#FBF7EF]"
            aria-label="Minimise Ask Sentinel"
          >
            <ChevronDown className="h-4 w-4" strokeWidth={2} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-hidden bg-card">
          <ExploreChat
            items={items}
            level={level}
            impact={impact}
            risk={risk}
            variant="overlay"
          />
        </div>
      </section>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className={cn(
          "ask-sentinel-fab group pointer-events-auto flex items-center gap-2.5 rounded-full border px-4 py-2.5 text-sm shadow-lg transition-colors",
          open
            ? "border-[#220F08] bg-[#220F08] text-[#FBF7EF]"
            : "border-border bg-card text-foreground hover:bg-secondary"
        )}
      >
        <AskSentinelMark
          className={cn(
            "ask-sentinel-sparkle h-5 w-5 transition-transform duration-300 group-hover:scale-110",
            open ? "text-[#DAA849]" : "text-olive"
          )}
        />
        <span className="font-medium tracking-tight">
          {open ? "Close" : "Ask Sentinel"}
        </span>
      </button>
    </div>
  );
}
