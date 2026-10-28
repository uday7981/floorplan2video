"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { AlertTriangle, Check, ArrowRight } from "lucide-react";
import { PlanEditor } from "@/components/plan/PlanEditor";
import { Button } from "@/components/ui/Button";
import { Hairline } from "@/components/ui/Hairline";
import { MOCK_PLAN } from "@/lib/mock-data";
import type { Plan } from "@/lib/mock-data";

// three.js preview is client-only; dynamic-import keeps it out of the SSR bundle
// so the server can still render the editor pane fast.
const PlanPreview3D = dynamic(
  () => import("@/components/plan/PlanPreview3D").then((m) => m.PlanPreview3D),
  { ssr: false, loading: () => <PreviewLoading /> },
);

export default function PlanPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [plan, setPlan] = React.useState<Plan>(MOCK_PLAN);
  const [saved, setSaved] = React.useState<"saved" | "saving" | "edited">("saved");

  // Debounced "save" — in M7 this PUTs /v1/plans/{id} with the edited JSON.
  const saveTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  React.useEffect(() => {
    setSaved("edited");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      setSaved("saving");
      setTimeout(() => setSaved("saved"), 350);
    }, 1000);
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current); };
  }, [plan]);

  const stats = React.useMemo(() => ({
    walls: plan.walls.length,
    openings: plan.openings.length,
    rooms: plan.rooms.length,
    bbox: bbox(plan),
    confidence: plan.meta.confidence,
  }), [plan]);

  return (
    <section className="mx-auto flex max-w-page flex-col gap-6 px-6 md:px-sheet py-10">
      {/* header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <span className="caption">Step 02 — Plan review</span>
          <h1 className="font-display text-[clamp(28px,4vw,44px)] leading-[1.02] tracking-display">
            Check the geometry.
          </h1>
        </div>

        <div className="flex items-center gap-6">
          <SaveState state={saved} />
          <ConfidencePill value={stats.confidence} />
        </div>
      </header>

      {plan.meta.warnings.length > 0 && <WarningsBanner messages={plan.meta.warnings} />}

      {/* editor + preview */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <PaneHeader
            caption="2D overlay"
            title="Walls & openings"
            right={<Legend />}
          />
          <PlanEditor
            plan={plan}
            onChange={setPlan}
            className="aspect-[4/3] w-full border border-ink/15"
          />
        </div>

        <div className="lg:col-span-5">
          <PaneHeader caption="3D preview" title="Live model" />
          <PlanPreview3D plan={plan} className="aspect-[4/3] w-full border border-ink/15" />
          <PlanFacts stats={stats} />
        </div>
      </div>

      <Hairline className="mt-4" />

      {/* approve */}
      <footer className="flex flex-wrap items-center justify-between gap-4">
        <p className="max-w-[52ch] text-[13px] text-ink/60">
          Approve the plan to lock the geometry and auto-generate a shot list. You can
          still return to this screen before any paid step.
        </p>
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => router.push(`/p/${params.id}/upload`)}>
            Back to upload
          </Button>
          <Button onClick={() => router.push(`/p/${params.id}/shots`)}>
            Approve plan
            <ArrowRight size={16} strokeWidth={1.6} />
          </Button>
        </div>
      </footer>
    </section>
  );
}

/* ---------- small bits ---------- */

function PaneHeader({ caption, title, right }: { caption: string; title: string; right?: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-end justify-between">
      <div className="flex flex-col gap-0.5">
        <span className="caption">{caption}</span>
        <span className="font-display text-[18px] italic text-ink/80">{title}</span>
      </div>
      {right}
    </div>
  );
}

function SaveState({ state }: { state: "saved" | "saving" | "edited" }) {
  const label =
    state === "saved" ? "All changes saved"
      : state === "saving" ? "Saving…"
      : "Unsaved changes";
  const color =
    state === "saved" ? "text-ink/55"
      : state === "saving" ? "text-ink/70"
      : "text-sienna";
  return (
    <span className={`caption flex items-center gap-2 ${color}`}>
      <span className={`h-[6px] w-[6px] rounded-full ${state === "saved" ? "bg-ink/50" : state === "saving" ? "bg-ink/70 animate-pulse" : "bg-sienna"}`} />
      {label}
    </span>
  );
}

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const good = value >= 0.75;
  return (
    <div className="flex items-center gap-2 border border-ink/15 px-3 py-1.5">
      <span className="caption">Confidence</span>
      <span className={`mono-num text-[13px] ${good ? "text-ink/85" : "text-sienna"}`}>{pct}%</span>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-4 text-[11px] uppercase tracking-caption text-ink/55">
      <span className="flex items-center gap-1.5">
        <span className="h-[3px] w-5 bg-ink" />Exterior wall
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-[3px] w-5 bg-ink/60" />Partition
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-[3px] w-5 bg-sienna" />Entrance
      </span>
    </div>
  );
}

function WarningsBanner({ messages }: { messages: string[] }) {
  return (
    <div className="flex items-start gap-3 border border-sienna/40 bg-sienna/[0.05] px-4 py-3">
      <AlertTriangle size={16} strokeWidth={1.6} className="mt-0.5 text-sienna" />
      <div className="flex flex-col gap-1">
        <span className="caption text-sienna">Needs a look</span>
        <ul className="text-[13px] text-ink/80 list-disc pl-5">
          {messages.map((m, i) => (<li key={i}>{m}</li>))}
        </ul>
      </div>
    </div>
  );
}

function PlanFacts({ stats }: { stats: { walls: number; openings: number; rooms: number; bbox: ReturnType<typeof bbox> } }) {
  return (
    <dl className="mt-3 grid grid-cols-4 gap-x-4 border-t border-ink/10 pt-3 text-[12px]">
      {[
        ["Walls", stats.walls],
        ["Openings", stats.openings],
        ["Rooms", stats.rooms],
        ["Bbox", `${stats.bbox.w.toFixed(1)}×${stats.bbox.h.toFixed(1)} m`],
      ].map(([k, v]) => (
        <div key={String(k)} className="flex flex-col gap-0.5">
          <dt className="caption text-ink/50">{k}</dt>
          <dd className="mono-num text-[14px] text-ink/85">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function bbox(plan: Plan) {
  const xs: number[] = []; const ys: number[] = [];
  for (const w of plan.walls) { xs.push(w.a[0], w.b[0]); ys.push(w.a[1], w.b[1]); }
  return { w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
}

function PreviewLoading() {
  return (
    <div className="flex aspect-[4/3] w-full items-center justify-center border border-ink/15 bg-paper-dim/40">
      <span className="caption animate-pulse text-ink/55">Loading model…</span>
    </div>
  );
}
