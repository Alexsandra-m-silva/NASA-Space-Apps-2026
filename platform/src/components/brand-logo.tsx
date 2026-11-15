"use client";

import { brand } from "@/data/brand";
import { cn } from "@/lib/utils";

export function BrandLogo({
  variant,
  className,
}: {
  /** onDark = mel wordmark; onLight = barro wordmark (vector, 2033×730) */
  variant: "onDark" | "onLight";
  className?: string;
  /** Kept for call-site compatibility with the header. */
  priority?: boolean;
}) {
  const src = brand.logo[variant];
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={brand.name}
      width={203}
      height={73}
      className={cn("h-10 w-auto sm:h-11", className)}
      draggable={false}
    />
  );
}
