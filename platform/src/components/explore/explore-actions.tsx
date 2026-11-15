"use client";

import { useEffect, useRef, useState } from "react";
import { Link2, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  LEVEL_LABELS,
  type GeoLevel,
  type RankingLens,
  type Territory,
} from "@/data/explore/types";

function SocialIcon({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden
      className={className ?? "size-4 shrink-0"}
      fill="currentColor"
    >
      {children}
    </svg>
  );
}

function XIcon() {
  return (
    <SocialIcon>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.727-8.913L1.254 2.25H8.08l4.253 5.622L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z" />
    </SocialIcon>
  );
}

function LinkedInIcon() {
  return (
    <SocialIcon>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 1.881 4.267 4.328v6.413zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </SocialIcon>
  );
}

function FacebookIcon() {
  return (
    <SocialIcon>
      <path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 22.613 10.125 23.854V15.46H7.078v-3.387h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.387h-2.796v8.394C19.612 22.613 24 18.1 24 12.073z" />
    </SocialIcon>
  );
}

export function ExploreShareActions({
  items,
  level,
  lens,
}: {
  items: Territory[];
  level: GeoLevel;
  lens: RankingLens;
}) {
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  function flash(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2200);
  }

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const url = typeof window !== "undefined" ? window.location.href : "";
  const title = "Climate Sentinel — exploration";
  const text = `View: ${LEVEL_LABELS[level]} · lens ${lens} · ${items.length} territories`;
  const encodedUrl = encodeURIComponent(url);
  const encodedText = encodeURIComponent(`${text}\n${url}`);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      flash("Link copied");
      setOpen(false);
    } catch {
      flash("Could not copy link");
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
      >
        <Share2 />
        Share
      </Button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-2 w-56 rounded-md border border-border bg-card p-1.5 shadow-md animate-rise"
        >
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-foreground hover:bg-secondary"
            onClick={copyLink}
          >
            <Link2 className="size-4 shrink-0" />
            Copy link
          </button>
          <a
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm text-foreground hover:bg-secondary"
            href={`https://twitter.com/intent/tweet?text=${encodedText}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            <XIcon />
            X
          </a>
          <a
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm text-foreground hover:bg-secondary"
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            <LinkedInIcon />
            LinkedIn
          </a>
          <a
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm text-foreground hover:bg-secondary"
            href={`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            <FacebookIcon />
            Facebook
          </a>
          {typeof navigator !== "undefined" && "share" in navigator && (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-foreground hover:bg-secondary"
              onClick={async () => {
                try {
                  await navigator.share({ title, text, url });
                  flash("Shared");
                  setOpen(false);
                } catch {
                  /* cancelled */
                }
              }}
            >
              <Share2 className="size-4 shrink-0" />
              More options…
            </button>
          )}
        </div>
      )}

      {toast && (
        <span className="absolute -bottom-7 right-0 whitespace-nowrap text-xs text-signal animate-rise">
          {toast}
        </span>
      )}
    </div>
  );
}
