import { cn } from "@/lib/utils";

/** Chat + AI mark from brand — fills with currentColor. */
export function AskSentinelMark({
  className,
  title,
}: {
  className?: string;
  title?: string;
}) {
  return (
    <span
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      className={cn(
        "inline-block shrink-0 bg-current",
        "[mask-image:url(/brand/ask-sentinel-mark.png)] [mask-size:contain] [mask-repeat:no-repeat] [mask-position:center]",
        "[-webkit-mask-image:url(/brand/ask-sentinel-mark.png)] [-webkit-mask-size:contain] [-webkit-mask-repeat:no-repeat] [-webkit-mask-position:center]",
        className
      )}
    />
  );
}
