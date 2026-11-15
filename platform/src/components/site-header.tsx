"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Contrast = "dark" | "light";

function contrastUnderHeader(headerHeight: number): Contrast {
  // Probe the strip the header covers, but ignore the header tree so we
  // read the page section underneath (hero/CTA), not the header chrome.
  const probeY = Math.max(4, Math.round(headerHeight * 0.5));
  const probeX = Math.round(window.innerWidth / 2);
  const stack = document
    .elementsFromPoint(probeX, probeY)
    .filter(
      (node): node is HTMLElement =>
        node instanceof HTMLElement && !node.closest("[data-site-header]")
    );

  for (const node of stack) {
    const marked = node.closest<HTMLElement>("[data-header-contrast]");
    if (marked?.dataset.headerContrast === "dark") return "dark";
    if (marked?.dataset.headerContrast === "light") return "light";
  }

  for (const node of stack) {
    let el: HTMLElement | null = node;
    while (el && el !== document.documentElement) {
      if (el.closest("[data-site-header]")) break;
      const bg = getComputedStyle(el).backgroundColor;
      const lum = luminanceOfCssColor(bg);
      if (lum != null) {
        return lum < 0.45 ? "dark" : "light";
      }
      el = el.parentElement;
    }
  }

  return "light";
}

function luminanceOfCssColor(color: string): number | null {
  const m = color.match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  const parts = m[1].split(",").map((p) => p.trim());
  const r = Number(parts[0]);
  const g = Number(parts[1]);
  const b = Number(parts[2]);
  const a = parts[3] != null ? Number(parts[3]) : 1;
  if (!Number.isFinite(r) || !Number.isFinite(g) || !Number.isFinite(b)) {
    return null;
  }
  if (a < 0.35) return null;
  const toLin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * toLin(r) + 0.7152 * toLin(g) + 0.0722 * toLin(b);
}

export function SiteHeader() {
  const pathname = usePathname();
  // Home hero is dark — start Mel wordmark to avoid a barro flash on load
  const [onDark, setOnDark] = useState(() => pathname === "/");

  useEffect(() => {
    setOnDark(pathname === "/");

    const header = document.querySelector<HTMLElement>("[data-site-header]");
    const headerHeight = header?.offsetHeight ?? 56;

    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        setOnDark(contrastUnderHeader(headerHeight) === "dark");
      });
    };

    // After paint so hero/sections exist under the fixed header
    frame = requestAnimationFrame(update);
    const t = window.setTimeout(update, 50);

    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(t);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [pathname]);

  return (
    <header
      data-site-header
      data-on-dark={onDark ? "true" : "false"}
      className={cn(
        "fixed inset-x-0 top-0 z-40 transition-colors duration-300",
        onDark
          ? "border-b border-white/15 bg-black/20 text-brand-areia backdrop-blur-md"
          : "border-b border-border/70 bg-card/80 text-foreground backdrop-blur-md"
      )}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link
          href="/"
          className="group relative flex items-center"
          aria-label="Climate Sentinel"
        >
          <span className="relative block h-7 w-[114px] sm:h-8 sm:w-[126px]">
            {/* Mel wordmark — dark backgrounds */}
            <BrandLogo
              variant="onDark"
              priority
              className={cn(
                "absolute inset-y-0 left-0 h-full w-auto transition-opacity duration-200",
                onDark ? "opacity-100" : "pointer-events-none opacity-0"
              )}
            />
            {/* Barro wordmark — light backgrounds */}
            <BrandLogo
              variant="onLight"
              priority
              className={cn(
                "absolute inset-y-0 left-0 h-full w-auto transition-opacity duration-200",
                onDark ? "pointer-events-none opacity-0" : "opacity-100"
              )}
            />
          </span>
        </Link>

        <nav className="flex items-center gap-3 text-sm sm:gap-4">
          <Link
            href="/about"
            className={cn(
              "rounded-md px-2 py-1.5 transition-colors",
              onDark
                ? "text-brand-areia/90 hover:bg-white/10 hover:text-brand-areia"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              (pathname === "/" || pathname === "/about") &&
                (onDark ? "text-brand-areia" : "text-foreground")
            )}
          >
            About
          </Link>
          <Link
            href="/explore"
            className={cn(
              "rounded-md px-2 py-1.5 transition-colors",
              onDark
                ? "text-brand-areia/90 hover:bg-white/10 hover:text-brand-areia"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
          >
            Explore
          </Link>
          <Button
            asChild
            size="sm"
            variant="accent"
            className="border-transparent bg-[#FFEA7F] text-[#220F08] shadow hover:bg-[#F5DE6E]"
          >
            <Link href="/newsletter">Newsletter</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
