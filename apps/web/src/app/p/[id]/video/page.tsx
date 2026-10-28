"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Check, Play, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Hairline } from "@/components/ui/Hairline";
import { MOCK_SHOTS, MOCK_TAKES, type MockTake } from "@/lib/mock-data";
import { cn } from "@/lib/cn";

const PRICE_PER_SECOND: Record<"480p" | "720p", number> = { "480p": 0.115, "720p": 0.249 };

export default function VideoPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [resolution, setResolution] = React.useState<"480p" | "720p">("480p");
  const [takes, setTakes] = React.useState<MockTake[]>(MOCK_TAKES);

  const total = MOCK_SHOTS.reduce((s, sh) => s + PRICE_PER_SECOND[resolution] * sh.duration_s, 0);
  const anySelected = takes.some((t) => t.selected);
  const selectedCount = new Set(takes.filter((t) => t.selected).map((t) => t.shot_id)).size;

  function selectTake(takeId: string) {
    const target = takes.find((t) => t.id === takeId);
    if (!target) return;
    setTakes((prev) => prev.map((t) =>
      t.shot_id === target.shot_id ? { ...t, selected: t.id === takeId } : t,
    ));
  }

  return (
    <section className="mx-auto flex max-w-page flex-col gap-10 px-6 md:px-sheet py-10">
      {/* header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <span className="caption">Step 04 — Video generation</span>
          <h1 className="font-display text-[clamp(28px,4vw,44px)] leading-[1.02] tracking-display">
            Render the walkthrough.
          </h1>
          <p className="max-w-[62ch] text-[14px] text-ink/60">
            Seedance 2.5 interpolates the CAD start frame into your approved photoreal end
            frame. Review the cost, pick a tier, and submit all shots in parallel.
          </p>
        </div>
      </header>

      {/* cost estimator */}
      <div className="grid grid-cols-1 gap-4 border border-ink/15 bg-paper md:grid-cols-12">
        {/* resolution toggle */}
        <div className="border-b border-ink/10 p-6 md:col-span-5 md:border-b-0 md:border-r">
          <span className="caption">Tier</span>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {(["480p", "720p"] as const).map((r) => (
              <label
                key={r}
                className={cn(
                  "cursor-pointer border px-4 py-4 transition-standard duration-standard",
                  resolution === r ? "border-ink bg-ink text-paper" : "border-ink/25 hover:border-ink/70",
                )}
              >
                <input type="radio" name="res" value={r} className="sr-only" checked={resolution === r} onChange={() => setResolution(r)} />
                <div className="flex items-start justify-between">
                  <div className="flex flex-col gap-1">
                    <span className="font-display text-[22px] italic leading-none">{r}</span>
                    <span className="text-[12px] opacity-70">
                      {r === "480p" ? "Draft tier" : "Final tier"}
                    </span>
                  </div>
                  <span className="mono-num text-[11px] opacity-70">${PRICE_PER_SECOND[r].toFixed(3)}/s</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* breakdown */}
        <div className="p-6 md:col-span-7">
          <span className="caption">Breakdown</span>
          <table className="mt-3 w-full border-separate border-spacing-0 text-[13px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-caption text-ink/50">
                <th className="pb-2 text-left font-medium">Shot</th>
                <th className="pb-2 text-left font-medium">Duration</th>
                <th className="pb-2 text-right font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_SHOTS.map((s) => (
                <tr key={s.id} className="border-t border-ink/5">
                  <td className="py-1.5 text-ink/85">{s.label}</td>
                  <td className="py-1.5 text-ink/60"><span className="mono-num">{s.duration_s}s</span></td>
                  <td className="py-1.5 text-right"><span className="mono-num">${(PRICE_PER_SECOND[resolution] * s.duration_s).toFixed(2)}</span></td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-ink/20">
                <td className="pt-3 caption text-ink/60">Total</td>
                <td />
                <td className="pt-3 text-right"><span className="mono-num text-[16px] text-ink">${total.toFixed(2)}</span></td>
              </tr>
            </tfoot>
          </table>
          <Button className="mt-6 w-full md:w-auto">
            <Sparkles size={14} strokeWidth={1.6} />
            Generate {MOCK_SHOTS.length} videos at {resolution} · ${total.toFixed(2)}
          </Button>
        </div>
      </div>

      {/* takes gallery */}
      <section className="flex flex-col gap-5">
        <header className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <span className="caption">Takes</span>
            <h2 className="font-display text-[22px] italic text-ink/85">Pick one per shot</h2>
          </div>
          <span className="mono-num text-[13px] text-ink/55">{selectedCount}/{MOCK_SHOTS.length} selected</span>
        </header>

        <div className="flex flex-col gap-6">
          {MOCK_SHOTS.map((shot) => {
            const shotTakes = takes.filter((t) => t.shot_id === shot.id);
            return (
              <div key={shot.id} className="border border-ink/10 bg-paper">
                <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
                  <div className="flex items-baseline gap-3">
                    <span className="mono-num text-[14px] text-ink/40">{String(shot.ord + 1).padStart(2, "0")}</span>
                    <span className="font-display text-[18px] italic">{shot.label}</span>
                  </div>
                  <Button size="sm" variant="secondary"><RefreshCw size={12} strokeWidth={1.6} /> Re-roll</Button>
                </div>
                {shotTakes.length === 0 ? (
                  <div className="p-5 text-[13px] italic text-ink/50">No takes yet.</div>
                ) : (
                  <div className="grid grid-cols-2 gap-3 p-5 md:grid-cols-3 lg:grid-cols-4">
                    {shotTakes.map((t) => (
                      <TakeCard key={t.id} take={t} onSelect={() => selectTake(t.id)} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <Hairline />

      <footer className="flex flex-wrap items-center justify-between gap-4">
        <p className="max-w-[52ch] text-[13px] text-ink/60">
          One take per shot moves forward to the export stitch. You can re-roll any shot
          without touching the others.
        </p>
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => router.push(`/p/${params.id}/shots`)}>Back</Button>
          <Button disabled={!anySelected} onClick={() => router.push(`/p/${params.id}/export`)}>
            Continue to export
          </Button>
        </div>
      </footer>
    </section>
  );
}

/* ---------- take card ---------- */

function TakeCard({ take, onSelect }: { take: MockTake; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group relative flex flex-col items-start gap-2 border p-2 text-left transition-standard duration-standard",
        take.selected ? "border-sienna bg-sienna/[0.05]" : "border-ink/15 hover:border-ink/55",
      )}
    >
      <div className="relative aspect-video w-full overflow-hidden bg-paper-dim">
        {/* abstract still — represents the mp4 */}
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(140deg, rgb(192 157 124 / 0.6) 0%, rgb(245 241 234) 50%, rgb(20 19 17 / 0.08) 100%)",
          }}
        />
        <div aria-hidden className="absolute inset-x-3 bottom-3 top-5 border border-ink/20" />

        <div className="absolute left-2 top-2 flex items-center gap-1 bg-paper/85 px-1.5 py-0.5 caption">
          <Play size={9} strokeWidth={2} /> {take.status}
        </div>
        {take.selected && (
          <div className="absolute right-2 top-2 flex items-center gap-1 bg-sienna text-paper px-1.5 py-0.5 caption">
            <Check size={9} strokeWidth={2.5} /> Selected
          </div>
        )}
      </div>

      <div className="flex w-full items-center justify-between pt-1">
        <span className="caption">Take {take.take} · {take.resolution}</span>
        <span className="mono-num text-[11px] text-ink/55">${take.usd.toFixed(2)}</span>
      </div>
    </button>
  );
}
