"use client";

import { brand } from "@/data/brand";
import { cn } from "@/lib/utils";

export function BrandLogo({
  variant,
  className,
}: {
  /** onDark = cream wordmark; onLight = barro wordmark */
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
      width={940}
      height={238}
      className={cn("h-7 w-auto sm:h-8", className)}
      draggable={false}
    />
  );
}
