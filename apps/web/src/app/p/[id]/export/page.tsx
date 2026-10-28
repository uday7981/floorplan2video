"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Download, Film } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Hairline } from "@/components/ui/Hairline";
import { MOCK_PROJECT, MOCK_SHOTS } from "@/lib/mock-data";

export default function ExportPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [title, setTitle] = React.useState(MOCK_PROJECT.name);
  const [captions, setCaptions] = React.useState<Record<string, string>>({});
  const [phase, setPhase] = React.useState<"idle" | "exporting" | "ready">("idle");
  const [progress, setProgress] = React.useState(0);

  async function stitch() {
    setPhase("exporting");
    for (let p = 0; p <= 100; p += 4) {
      await new Promise((r) => setTimeout(r, 90));
      setProgress(p);
    }
    setPhase("ready");
  }

  const totalDuration = MOCK_SHOTS.reduce((s, sh) => s + sh.duration_s, 0) + 2;

  return (
    <section className="mx-auto flex max-w-page flex-col gap-10 px-6 md:px-sheet py-10">
      <header className="flex flex-col gap-2">
        <span className="caption">Step 05 — Export</span>
        <h1 className="font-display text-[clamp(28px,4vw,44px)] leading-[1.02] tracking-display">
          Stitch and ship.
        </h1>
        <p className="max-w-[62ch] text-[14px] text-ink/60">
          ffmpeg joins your selected takes with 0.3 s crossfades, overlays room labels
          and a 2 s end card, and gives you a single H.264 MP4.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Preview area */}
        <div className="lg:col-span-7">
          <div
            className="relative aspect-video w-full overflow-hidden border border-ink/15 bg-ink"
            style={{
              background:
                "linear-gradient(135deg, rgb(20 19 17) 0%, rgb(31 58 95 / 0.3) 50%, rgb(192 157 124 / 0.4) 100%)",
            }}
          >
            {/* static representation of the final video */}
            <div aria-hidden className="absolute inset-x-12 bottom-14 top-16 border border-paper/20" />
            <div className="absolute left-6 bottom-6 flex items-center gap-2 bg-ink/50 px-2 py-1 caption text-paper">
              01 {MOCK_SHOTS[1]?.label ?? "Scene"}
            </div>
            {phase === "ready" ? (
              <button
                aria-label="Play final"
                className="absolute inset-0 flex items-center justify-center text-paper transition-standard duration-standard hover:bg-ink/10"
              >
                <span className="flex h-16 w-16 items-center justify-center rounded-full border border-paper/70 bg-ink/50 backdrop-blur">
                  <Film size={22} strokeWidth={1.4} />
                </span>
              </button>
            ) : phase === "exporting" ? (
              <div className="absolute inset-x-0 bottom-0">
                <div className="relative h-1 overflow-hidden">
                  <div className="absolute inset-0 bg-paper/10" />
                  <div className="absolute inset-y-0 left-0 bg-sienna transition-standard duration-standard" style={{ width: `${progress}%` }} />
                </div>
                <div className="flex items-center justify-between px-4 py-3 text-paper">
                  <span className="caption">Stitching</span>
                  <span className="mono-num text-[12px]">{progress}%</span>
                </div>
              </div>
            ) : null}
          </div>

          <dl className="mt-4 grid grid-cols-4 gap-x-4 border-t border-ink/10 pt-3 text-[12px]">
            {[
              ["Shots", MOCK_SHOTS.length],
              ["Duration", `${totalDuration}s`],
              ["Resolution", "1280×720"],
              ["Codec", "H.264"],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex flex-col gap-0.5">
                <dt className="caption text-ink/50">{k}</dt>
                <dd className="mono-num text-[14px] text-ink/85">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Right column: title + captions */}
        <aside className="lg:col-span-5">
          <div className="border border-ink/15 bg-paper">
            <div className="border-b border-ink/10 px-6 py-5">
              <span className="caption">Title card</span>
              <h2 className="mt-2 font-display text-[22px] leading-tight">End card title</h2>
            </div>
            <div className="flex flex-col gap-5 px-6 py-5">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
          </div>

          <div className="mt-6 border border-ink/15 bg-paper">
            <div className="border-b border-ink/10 px-6 py-5">
              <span className="caption">Per-shot captions (optional)</span>
            </div>
            <div className="flex flex-col divide-y divide-ink/5">
              {MOCK_SHOTS.map((s) => (
                <label key={s.id} className="flex items-center gap-4 px-6 py-3 text-[13px]">
                  <span className="mono-num shrink-0 text-ink/40 w-6">{String(s.ord + 1).padStart(2, "0")}</span>
                  <span className="font-display italic text-ink/85 w-28 shrink-0 truncate">{s.label}</span>
                  <input
                    className="flex-1 bg-transparent text-ink outline-none placeholder:text-ink/35"
                    placeholder="optional caption"
                    value={captions[s.id] ?? ""}
                    onChange={(e) => setCaptions((p) => ({ ...p, [s.id]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
          </div>
        </aside>
      </div>

      <Hairline />

      <footer className="flex flex-wrap items-center justify-between gap-4">
        <p className="max-w-[52ch] text-[13px] text-ink/60">
          Export stitches on the GPU pod and uploads to the exports bucket. A copy stays
          available for 30 days.
        </p>
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => router.push(`/p/${params.id}/video`)}>Back</Button>
          {phase === "ready" ? (
            <Button>
              <Download size={16} strokeWidth={1.6} />
              Download MP4
            </Button>
          ) : (
            <Button onClick={stitch} disabled={phase === "exporting"}>
              {phase === "exporting" ? "Exporting…" : "Export walkthrough"}
            </Button>
          )}
        </div>
      </footer>
    </section>
  );
}
