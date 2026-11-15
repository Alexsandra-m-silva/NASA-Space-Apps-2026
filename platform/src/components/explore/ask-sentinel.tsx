"use client";

import { useEffect, useId, useRef, useState } from "react";
import { X } from "lucide-react";
import { AskSentinelMark } from "@/components/explore/ask-sentinel-mark";
import { ExploreChat } from "@/components/explore/explore-chat";
import { cn } from "@/lib/utils";
import type {
  GeoLevel,
  ImpactType,
  RiskLevel,
  Territory,
} from "@/data/explore/types";

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
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={cn(
          "ask-sentinel-fab group fixed bottom-5 right-2 z-40 flex items-center gap-2.5 rounded-md border px-3.5 py-2.5 text-sm sm:bottom-6 sm:right-3",
          "border-border/70 bg-card/80 text-foreground backdrop-blur-md",
          "hover:bg-card/95"
        )}
      >
        <AskSentinelMark className="ask-sentinel-sparkle h-5 w-5 text-olive transition-transform duration-300 group-hover:scale-110" />
        <span className="font-medium tracking-tight">Ask Sentinel</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center p-3 sm:items-center sm:p-6">
          <button
            type="button"
            aria-label="Close Ask Sentinel"
            className="absolute inset-0 bg-[#220F08]/45 backdrop-blur-[2px]"
            onClick={() => setOpen(false)}
          />

          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className={cn(
              "relative z-10 flex w-full max-w-lg flex-col overflow-hidden rounded-md border shadow-lg",
              "max-h-[min(88vh,640px)]",
              "border-border/70 bg-card/90 text-foreground backdrop-blur-md"
            )}
          >
            <div className="flex items-center justify-between gap-3 border-b border-border/70 px-4 py-3">
              <div className="flex min-w-0 items-center gap-2.5">
                <AskSentinelMark className="h-5 w-5 text-olive" />
                <h2
                  id={titleId}
                  className="truncate font-display text-lg text-olive"
                >
                  Ask Sentinel
                </h2>
              </div>
              <button
                ref={closeRef}
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                aria-label="Close"
              >
                <X className="h-4 w-4" strokeWidth={1.75} />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-hidden">
              <ExploreChat
                items={items}
                level={level}
                impact={impact}
                risk={risk}
                variant="overlay"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
