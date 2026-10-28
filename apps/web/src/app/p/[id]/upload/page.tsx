"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, FileText, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/cn";

type Phase = "idle" | "uploading" | "extracting";

/**
 * Upload a floor plan. Drop zone → mock upload → mock extraction progress →
 * redirect to /plan. Real upload uses the signed upload URL from
 * /v1/projects/{id}/plans/upload-url and PUTs the file bytes directly to
 * Supabase storage. Extraction is enqueued separately and polled via
 * Supabase realtime on the `jobs` table (M7).
 */
export default function UploadPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [phase, setPhase] = React.useState<Phase>("idle");
  const [progress, setProgress] = React.useState(0);
  const [file, setFile] = React.useState<File | null>(null);
  const [dim, setDim] = React.useState("");
  const [drag, setDrag] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const onPick = React.useCallback((f: File | null) => {
    if (!f) return;
    const ok = /(image|pdf)/.test(f.type) || /\.(png|jpg|jpeg|webp|heic|pdf|dxf)$/i.test(f.name);
    if (!ok) {
      alert("Supported: PNG, JPG, WEBP, HEIC, PDF, DXF");
      return;
    }
    setFile(f);
  }, []);

  async function start() {
    if (!file) return;
    setPhase("uploading");
    for (let p = 0; p <= 100; p += 10) {
      await new Promise((r) => setTimeout(r, 60));
      setProgress(p);
    }
    setPhase("extracting");
    for (let p = 0; p <= 100; p += 4) {
      await new Promise((r) => setTimeout(r, 70));
      setProgress(p);
    }
    router.push(`/p/${params.id}/plan`);
  }

  return (
    <section className="mx-auto flex max-w-page flex-col gap-10 px-6 md:px-sheet py-12">
      <header className="flex flex-col gap-3">
        <span className="caption">Step 01 — Upload</span>
        <h1 className="font-display text-[clamp(32px,5vw,56px)] leading-[1.02] tracking-display">
          Hand us the plan.
        </h1>
        <p className="max-w-[62ch] text-[15px] leading-[1.65] text-ink/65">
          PNG, JPG, PDF or DXF — up to 50 MB. A single-storey floor plan, drawn
          to scale with any legible dimension line. We'll read it with Claude
          and come back with editable walls and rooms.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
        {/* Drop zone */}
        <div className="lg:col-span-8">
          <div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              onPick(e.dataTransfer.files[0] ?? null);
            }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "relative flex min-h-[320px] cursor-pointer flex-col items-center justify-center gap-6 border border-dashed p-10 text-center transition-standard duration-standard",
              drag ? "border-sienna bg-sienna/[0.04]" : "border-ink/25 bg-paper-dim/40 hover:border-ink/60",
            )}
          >
            {file ? (
              <div className="flex flex-col items-center gap-4">
                <FileText size={28} strokeWidth={1.3} className="text-ink/70" />
                <div className="flex flex-col gap-1">
                  <span className="font-display text-[22px] italic">{file.name}</span>
                  <span className="caption text-ink/55">
                    {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type || "unknown"}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="text-[13px] text-ink/55 underline underline-offset-4 hover:text-sienna"
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <>
                <UploadCloud size={44} strokeWidth={1.2} className="text-ink/40" />
                <div className="flex flex-col gap-2">
                  <span className="font-display text-[26px] leading-tight tracking-display">
                    Drop a floor plan here
                  </span>
                  <span className="text-[13px] text-ink/55">or click to browse</span>
                </div>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              className="sr-only"
              accept=".png,.jpg,.jpeg,.webp,.heic,.pdf,.dxf,image/*,application/pdf"
              onChange={(e) => onPick(e.target.files?.[0] ?? null)}
            />
          </div>

          {phase !== "idle" && (
            <div className="mt-6 flex flex-col gap-3">
              <div className="flex items-end justify-between">
                <span className="caption">
                  {phase === "uploading" ? "Uploading" : "Extracting with Claude"}
                </span>
                <span className="mono-num text-[13px] text-ink/70">{progress}%</span>
              </div>
              <div className="relative h-[2px] overflow-hidden">
                <div className="absolute inset-0 bg-ink/10" />
                <div
                  className="absolute inset-y-0 left-0 bg-ink transition-standard duration-standard"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-[12px] text-ink/50 italic font-display">
                {phase === "uploading"
                  ? "Sending to our drafting table…"
                  : "Reading walls, openings, rooms, scale…"}
              </p>
            </div>
          )}
        </div>

        {/* Side column — options */}
        <aside className="lg:col-span-4">
          <div className="border border-ink/10 bg-paper">
            <div className="border-b border-ink/10 px-6 py-5">
              <span className="caption">Optional</span>
              <h2 className="mt-2 font-display text-[22px] leading-tight">Known dimension</h2>
            </div>
            <div className="flex flex-col gap-5 px-6 py-5">
              <p className="text-[13px] leading-[1.6] text-ink/60">
                If the plan has no scale bar, give us one dimension in metres and we'll
                anchor the scale to it. Overall width works best.
              </p>
              <Input
                type="number"
                step="0.01"
                label="Metres"
                placeholder="12.5"
                value={dim}
                onChange={(e) => setDim(e.target.value)}
              />
            </div>
          </div>

          <div className="mt-6 border border-ink/10 bg-paper">
            <div className="border-b border-ink/10 px-6 py-5">
              <span className="caption">Supported inputs</span>
            </div>
            <ul className="flex flex-col gap-2 px-6 py-5 text-[13px] text-ink/70">
              {["PNG · JPG · WEBP · HEIC", "PDF — multi-page or single", "DXF — exported from CAD"].map((s) => (
                <li key={s} className="flex items-center gap-3">
                  <span className="h-[3px] w-[3px] rounded-full bg-ink/50" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>

      <footer className="flex items-center justify-end gap-4 border-t border-ink/10 pt-6">
        <Button variant="ghost" onClick={() => router.push("/")}>Cancel</Button>
        <Button onClick={start} disabled={!file || phase !== "idle"}>
          {phase === "idle" ? (
            <>
              Extract plan
              <ArrowRight size={16} strokeWidth={1.6} />
            </>
          ) : phase === "uploading" ? "Uploading…" : "Reading plan…"}
        </Button>
      </footer>
    </section>
  );
}
