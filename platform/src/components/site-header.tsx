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

  const linkTone = onDark
    ? "text-brand-areia/90 hover:bg-white/10 hover:text-brand-areia"
    : "text-muted-foreground hover:bg-secondary hover:text-foreground";

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
      <div className="mx-auto grid max-w-6xl grid-cols-[1fr_auto_1fr] items-center gap-2 px-4 py-3 sm:gap-4 sm:px-6">
        <Link
          href="/"
          className="group relative flex items-center justify-self-start"
          aria-label="Climate Sentinel"
        >
          <span className="relative block h-10 w-[112px] sm:h-11 sm:w-[122px]">
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

        <Button
          asChild
          size="sm"
          variant="tertiary"
          className={cn(
            "justify-self-center gap-1.5 px-2 font-medium shadow-none",
            linkTone
          )}
        >
          <a
            href="https://github.com/Alexsandra-m-silva/NASA-Space-Apps-2026/pulse"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              aria-hidden
              viewBox="0 0 98 96"
              className="size-3.5 shrink-0 fill-current sm:size-4"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.528 33.405-24.934 33.405-46.691C97.707 22 75.788 0 48.854 0z"
              />
            </svg>
            <span className="max-sm:sr-only">Github repository</span>
            <span className="sm:hidden">Github</span>
          </a>
        </Button>

        <nav className="flex items-center justify-self-end gap-2 text-sm sm:gap-4">
          <Link
            href="/about"
            className={cn(
              "rounded-md px-2 py-1.5 transition-colors",
              linkTone,
              (pathname === "/" || pathname === "/about") &&
                (onDark ? "text-brand-areia" : "text-foreground")
            )}
          >
            About
          </Link>
          <Link
            href="/team"
            className={cn(
              "whitespace-nowrap rounded-md px-2 py-1.5 transition-colors",
              linkTone,
              pathname === "/team" &&
                (onDark ? "text-brand-areia" : "text-foreground")
            )}
          >
            The&nbsp;Team
          </Link>
          <Link
            href="/explore"
            className={cn(
              "rounded-md px-2 py-1.5 transition-colors",
              linkTone,
              pathname === "/explore" &&
                (onDark ? "text-brand-areia" : "text-foreground")
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
