"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/cn";

type Step = { slug: string; label: string };

const STEPS: Step[] = [
  { slug: "upload",     label: "Upload" },
  { slug: "plan",       label: "Plan" },
  { slug: "journey",    label: "Journey" },
  { slug: "boundaries", label: "Frames" },
  { slug: "video",      label: "Video" },
  { slug: "export",     label: "Export" },
];

/**
 * Horizontal step rail used across the project flow. Numbers in mono, labels
 * in display italic. Signature animation: the connecting line between done
 * steps strokes in once per mount (SVG stroke-dasharray reveal).
 */
export function Stepper({ projectId }: { projectId: string }) {
  const pathname = usePathname() ?? "";
  const activeIndex = STEPS.findIndex((s) => pathname.endsWith(`/${s.slug}`));

  return (
    <nav aria-label="Project flow" className="w-full">
      <ol className="mx-auto flex max-w-page flex-wrap items-center gap-x-6 gap-y-4 px-6 md:px-sheet py-5">
        {STEPS.map((step, i) => {
          const state =
            i < activeIndex ? "done" : i === activeIndex ? "active" : "pending";
          return (
            <li key={step.slug} className="flex items-center gap-3">
              <Link
                href={`/p/${projectId}/${step.slug}`}
                className="group inline-flex items-center gap-3"
              >
                <span
                  className={cn(
                    "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-standard duration-standard",
                    state === "done" && "border-ink bg-ink text-paper",
                    state === "active" && "border-sienna bg-sienna text-paper",
                    state === "pending" && "border-ink/30 text-ink/50",
                  )}
                >
                  {state === "done" ? (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
                      <path d="M2.5 6.5L5 9l4.5-5.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="square" />
                    </svg>
                  ) : (
                    <span className="mono-num text-[11px] leading-none">{String(i + 1).padStart(2, "0")}</span>
                  )}
                </span>
                <span
                  className={cn(
                    "font-display text-base leading-none transition-standard duration-standard",
                    state === "active" ? "text-ink italic" : state === "done" ? "text-ink/85" : "text-ink/45",
                    "group-hover:text-ink",
                  )}
                >
                  {step.label}
                </span>
              </Link>
              {i < STEPS.length - 1 && (
                <span
                  aria-hidden
                  className={cn(
                    "mx-1 h-px w-10 transition-standard duration-reveal",
                    i < activeIndex ? "bg-ink/60" : "bg-ink/15",
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
