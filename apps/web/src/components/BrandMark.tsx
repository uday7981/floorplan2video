import Link from "next/link";
import { cn } from "@/lib/cn";

/**
 * Brand mark: a drafter's "FP" monogram set as a tiny engraved stamp.
 * The subtle 1px ink hairline echoes the drafting-line aesthetic.
 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("inline-flex items-center gap-3 group", className)}>
      <svg
        width="28"
        height="28"
        viewBox="0 0 28 28"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="transition-standard duration-standard group-hover:rotate-3"
        aria-hidden
      >
        <rect
          x="1.5"
          y="1.5"
          width="25"
          height="25"
          rx="2"
          stroke="rgb(var(--ink))"
          strokeOpacity="0.9"
          strokeWidth="1"
        />
        <path
          d="M8 20V8h12M8 14h8"
          stroke="rgb(var(--ink))"
          strokeOpacity="0.9"
          strokeWidth="1.4"
          strokeLinecap="square"
        />
        <circle cx="22" cy="22" r="2.2" fill="rgb(var(--sienna))" />
      </svg>
      <span className="font-display text-lg leading-none tracking-tight">
        Floorplan<span className="text-ink/50"> / </span>Video
      </span>
    </Link>
  );
}
