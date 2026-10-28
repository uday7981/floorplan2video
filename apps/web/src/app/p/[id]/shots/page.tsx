"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Check, ArrowRight, RefreshCw, Play } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Hairline } from "@/components/ui/Hairline";
import { MOCK_SHOTS, type MockShot } from "@/lib/mock-data";
import { cn } from "@/lib/cn";

const MOVE_LABEL: Record<MockShot["move"], string> = {
  dolly: "Dolly 1.5 m forward",
  pan:   "Pan left → right",
  crane: "Crane 2 m up",
  orbit: "Orbit 90°",
};

const KIND_LABEL: Record<MockShot["kind"], string> = {
  opening:  "Opening",
  room:     "Room",
  exterior: "Exterior",
};

export default function ShotsPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [shots, setShots] = React.useState<MockShot[]>(MOCK_SHOTS);

  function toggleApprove(id: string) {
    setShots((prev) => prev.map((s) => s.id === id ? { ...s, end_frame_approved: !s.end_frame_approved } : s));
  }

  const approved = shots.filter((s) => s.end_frame_approved).length;
  const allApproved = approved === shots.length;

  return (
    <section className="mx-auto flex max-w-page flex-col gap-10 px-6 md:px-sheet py-10">
      {/* header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <span className="caption">Step 03 — Shots &amp; frames</span>
          <h1 className="font-display text-[clamp(28px,4vw,44px)] leading-[1.02] tracking-display">
            Shape the walkthrough.
          </h1>
          <p className="max-w-[62ch] text-[14px] text-ink/60">
            One opening shot, one per room, plus an exterior orbit for houses. Each shot
            has a photoreal end frame — approve it or regenerate until it matches your taste.
          </p>
        </div>
        <div className="flex items-center gap-3 border border-ink/15 px-4 py-2.5">
          <span className="caption">End frames approved</span>
          <span className="mono-num text-[15px] text-ink/85">{approved}<span className="text-ink/35"> / {shots.length}</span></span>
        </div>
      </header>

      {/* shot list */}
      <div className="flex flex-col divide-y divide-ink/10 border-y border-ink/15">
        {shots.map((shot, i) => (
          <ShotRow key={shot.id} shot={shot} index={i} onToggleApprove={() => toggleApprove(shot.id)} />
        ))}
      </div>

      <Hairline />

      {/* footer actions */}
      <footer className="flex flex-wrap items-center justify-between gap-4">
        <p className="max-w-[54ch] text-[13px] text-ink/60">
          You can regenerate individual end frames without affecting the others. Once all
          are approved, proceed to the video step to lock in a cost and submit.
        </p>
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => router.push(`/p/${params.id}/plan`)}>Back</Button>
          <Button disabled={!allApproved} onClick={() => router.push(`/p/${params.id}/video`)}>
            {allApproved ? "Continue to video" : `${shots.length - approved} to approve`}
            {allApproved && <ArrowRight size={16} strokeWidth={1.6} />}
          </Button>
        </div>
      </footer>
    </section>
  );
}

/* ---------- row ---------- */

function ShotRow({ shot, index, onToggleApprove }: { shot: MockShot; index: number; onToggleApprove: () => void }) {
  return (
    <div className="grid grid-cols-1 gap-6 py-6 md:grid-cols-12">
      {/* ord + label */}
      <div className="md:col-span-2">
        <span className="mono-num text-[26px] text-ink/30">{String(index + 1).padStart(2, "0")}</span>
        <div className="mt-1 font-display text-[20px] italic">{shot.label}</div>
        <div className="caption mt-1 text-ink/55">{KIND_LABEL[shot.kind]} · {shot.duration_s}s</div>
      </div>

      {/* clay / driving preview placeholder */}
      <div className="md:col-span-4">
        <span className="caption">Driving clip</span>
        <div className="mt-2 relative aspect-video overflow-hidden border border-ink/15 bg-paper-dim/40">
          <div
            aria-hidden
            className="absolute inset-0 opacity-80"
            style={{
              backgroundImage:
                "repeating-linear-gradient(0deg, rgba(31,58,95,0.08) 0 1px, transparent 1px 24px), " +
                "repeating-linear-gradient(90deg, rgba(31,58,95,0.08) 0 1px, transparent 1px 24px)",
            }}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <button
              aria-label="Play driving clip"
              className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/40 bg-paper transition-standard duration-standard hover:border-ink hover:bg-ink hover:text-paper"
            >
              <Play size={14} strokeWidth={1.6} />
            </button>
          </div>
          <div className="absolute left-2 top-2 caption text-ink/50">Workbench · 1280×720</div>
          <div className="absolute right-2 bottom-2 caption text-ink/50">{MOVE_LABEL[shot.move]}</div>
        </div>
      </div>

      {/* end frame */}
      <div className="md:col-span-4">
        <span className="caption">End frame</span>
        <div
          className={cn(
            "mt-2 relative aspect-video overflow-hidden border transition-standard duration-standard",
            shot.end_frame_approved ? "border-ink/70" : "border-ink/15",
          )}
          style={{
            background:
              "linear-gradient(135deg, rgb(245 241 234) 0%, rgb(235 231 223) 50%, rgb(192 157 124 / 0.55) 100%)",
          }}
        >
          {/* abstract architectural still — stand-in for the photoreal frame */}
          <div aria-hidden className="absolute inset-x-6 bottom-6 top-10 border border-ink/25" />
          <div aria-hidden className="absolute inset-x-10 bottom-10 top-16 border border-ink/15" />
          <div className="absolute left-2 top-2 caption text-ink/50">1280×720 · 1792 → cropped</div>
          {shot.end_frame_approved && (
            <div className="absolute right-2 top-2 flex items-center gap-1.5 bg-ink text-paper px-2 py-1 caption">
              <Check size={10} strokeWidth={2} /> Approved
            </div>
          )}
        </div>
      </div>

      {/* actions */}
      <div className="flex flex-col items-start gap-2 md:col-span-2 md:items-end">
        <Button size="sm" variant="secondary" className="w-full md:w-auto">
          <RefreshCw size={13} strokeWidth={1.6} /> Regenerate
        </Button>
        <Button
          size="sm"
          variant={shot.end_frame_approved ? "ghost" : "primary"}
          onClick={onToggleApprove}
          className="w-full md:w-auto"
        >
          {shot.end_frame_approved ? "Unapprove" : "Approve"}
        </Button>
      </div>
    </div>
  );
}
