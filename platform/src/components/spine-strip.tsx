import { evidenceSpine } from "@/data/spine";

export function SpineStrip({ className = "" }: { className?: string }) {
  return (
    <ol
      className={`flex flex-col gap-3 md:flex-row md:flex-wrap md:items-stretch md:gap-2 ${className}`}
    >
      {evidenceSpine.map((node, index) => (
        <li key={node.id} className="flex flex-1 items-stretch gap-2 min-w-[9.5rem]">
          <div className="flex flex-1 flex-col rounded-md border border-border bg-card/80 p-3 shadow-sm">
            <span className="mb-1 font-sans text-[0.65rem] uppercase tracking-[0.16em] text-signal">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="font-display text-sm leading-snug text-olive">
              {node.label}
            </span>
          </div>
          {index < evidenceSpine.length - 1 && (
            <div
              aria-hidden
              className="hidden w-3 shrink-0 self-center md:block"
            >
              <svg viewBox="0 0 12 12" className="h-3 w-3 text-earth">
                <path
                  d="M1 6h8M7 3l3 3-3 3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="animate-draw"
                  strokeDasharray="120"
                />
              </svg>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
