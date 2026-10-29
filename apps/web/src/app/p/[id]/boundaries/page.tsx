"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Hairline } from "@/components/ui/Hairline";
import { ArrowRight, Check, RefreshCw } from "lucide-react";
import { MOCK_SHOTS } from "@/lib/mock-data";
import { cn } from "@/lib/cn";

// Mocked: pretend each adjacent pair of walkthrough shots is a boundary.
// A real build pulls boundaries[] from journey.json via the API.
const BOUNDARIES = Array.from({ length: Math.max(0, MOCK_SHOTS.length) }, (_, i) => ({
  ord: i,
  kind: i === 0 ? ("cad" as const) : ("photoreal" as const),
  approved: i < 2,
}));

export default function BoundariesPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const approved = BOUNDARIES.filter((b) => b.approved).length;
  const total = BOUNDARIES.length;
  const allApproved = approved === total;

  return (
    <section className="mx-auto flex max-w-page flex-col gap-10 px-6 md:px-sheet py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <span className="caption">Step 04 — Boundary frames</span>
          <h1 className="font-display text-[clamp(28px,4vw,44px)] leading-[1.02] tracking-display">
            Approve the frames between segments.
          </h1>
          <p className="max-w-[62ch] text-[14px] text-ink/60">
            Each boundary is shared by the two segments that meet at it — the
            end frame of segment N and the start frame of segment N+1. One
            approval locks it on both sides.
          </p>
        </div>
        <div className="flex items-center gap-3 border border-ink/15 px-4 py-2.5">
          <span className="caption">Approved</span>
          <span className="mono-num text-[15px] text-ink/85">
            {approved}<span className="text-ink/35"> / {total}</span>
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        {BOUNDARIES.map((b) => (
          <article
            key={b.ord}
            className={cn(
              "flex flex-col gap-3 border p-4",
              b.approved ? "border-ink/70" : "border-ink/15",
            )}
          >
            <header className="flex items-center justify-between">
              <span className="caption">Boundary {String(b.ord).padStart(2, "0")}</span>
              <span className="caption text-ink/50">{b.kind}</span>
            </header>
            <div
              className="aspect-video border border-ink/10"
              style={{
                background:
                  b.kind === "cad"
                    ? "linear-gradient(135deg,#fff,#f5f1ea)"
                    : "linear-gradient(135deg, rgba(192,157,124,.6) 0%, rgba(245,241,234,1) 50%, rgba(20,19,17,.08) 100%)",
              }}
            />
            <div className="flex items-center justify-between">
              <Button size="sm" variant="secondary">
                <RefreshCw size={13} strokeWidth={1.6} /> Regenerate
              </Button>
              <Button size="sm" variant={b.approved ? "ghost" : "primary"}>
                {b.approved ? "Approved" : "Approve"}
                {b.approved && <Check size={13} strokeWidth={2} />}
              </Button>
            </div>
          </article>
        ))}
      </div>

      <Hairline />

      <footer className="flex flex-wrap items-center justify-between gap-4">
        <p className="max-w-[52ch] text-[13px] text-ink/60">
          Boundary 00 is the CAD-style opening frame; the rest are photoreal
          and go to Seedance as both the end of one segment and the start of
          the next.
        </p>
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => router.push(`/p/${params.id}/journey`)}>
            Back
          </Button>
          <Button disabled={!allApproved} onClick={() => router.push(`/p/${params.id}/video`)}>
            Continue to video
            {allApproved && <ArrowRight size={16} strokeWidth={1.6} />}
          </Button>
        </div>
      </footer>
    </section>
  );
}
