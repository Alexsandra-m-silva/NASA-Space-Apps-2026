"use client";

import { brand } from "@/data/brand";
import { cn } from "@/lib/utils";

export function BrandLogo({
  variant,
  className,
}: {
  /** onDark = official Sand SVG; onLight = official Horizontal SVG */
  variant: "onDark" | "onLight";
  className?: string;
  /** Kept for call-site compatibility with the header. */
  priority?: boolean;
}) {
  const src = brand.logo[variant];
  return (
    // Official SVGs from the NASA Space App Challenge Design System zip.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={brand.name}
      width={318}
      height={48}
      className={cn("h-8 w-auto sm:h-9", className)}
      draggable={false}
    />
  );
}
