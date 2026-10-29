"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Dialog, DialogClose, DialogContent, DialogTrigger } from "./ui/Dialog";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";
import type { Project, ProjectType, StoreyMode } from "@/lib/types";

const PRESETS = [
  {
    id: "oak",
    label: "Oak · black aluminium · natural white",
    style_preset: {
      materials: "oak, black aluminium, natural white",
      light: "3000K",
      setting: "a beautiful forest",
    },
  },
  {
    id: "concrete",
    label: "Concrete · steel · white",
    style_preset: {
      materials: "concrete, steel, white",
      light: "4000K",
      setting: "an overcast sky",
    },
  },
  {
    id: "walnut",
    label: "Walnut · aluminium · charcoal",
    style_preset: {
      materials: "walnut, aluminium, charcoal",
      light: "2700K",
      setting: "a dusk landscape",
    },
  },
] as const;

export function NewProjectDialog({
  onCreate,
}: {
  onCreate: (p: { name: string; project_type: ProjectType; storey_mode: StoreyMode; style_preset: Record<string, string> }) => Promise<Project>;
}) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [kind, setKind] = React.useState<ProjectType>("house");
  const [storey, setStorey] = React.useState<StoreyMode>("single");
  const [preset, setPreset] = React.useState<typeof PRESETS[number]["id"]>("oak");
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const style = PRESETS.find((p) => p.id === preset)!.style_preset;
      const created = await onCreate({ name: name.trim(), project_type: kind, storey_mode: storey, style_preset: style });
      setOpen(false);
      router.push(`/p/${created.id}/upload`);
    } catch (e: any) {
      setErr(e?.message ?? "Could not create project");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="md">New project</Button>
      </DialogTrigger>
      <DialogContent
        title="Begin a new sheet"
        description="Name the project and pick a material palette. You can edit everything later."
      >
        <form onSubmit={submit} className="flex flex-col gap-7">
          <Input
            label="Project name"
            placeholder="Oakhill Residence"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />

          <fieldset className="flex flex-col gap-3">
            <legend className="caption">Type</legend>
            <div className="flex gap-3">
              {(["house", "interior"] as const).map((v) => (
                <label
                  key={v}
                  className={
                    "flex-1 cursor-pointer border px-4 py-3 text-[14px] transition-standard duration-standard " +
                    (kind === v
                      ? "border-ink bg-ink text-paper"
                      : "border-ink/25 text-ink hover:border-ink/70")
                  }
                >
                  <input
                    type="radio"
                    name="kind"
                    value={v}
                    checked={kind === v}
                    onChange={() => setKind(v)}
                    className="sr-only"
                  />
                  <span className="font-display italic text-[17px] leading-none">
                    {v === "house" ? "House" : "Interior"}
                  </span>
                  <span className="mt-1 block text-[11px] opacity-70">
                    {v === "house"
                      ? "Opening + rooms + exterior orbit"
                      : "Opening + rooms (no exterior)"}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="flex flex-col gap-3">
            <legend className="caption">Floors</legend>
            <div className="flex gap-3">
              {(["single", "multi"] as const).map((v) => (
                <label
                  key={v}
                  className={
                    "flex-1 cursor-pointer border px-4 py-3 text-[14px] transition-standard duration-standard " +
                    (storey === v
                      ? "border-ink bg-ink text-paper"
                      : "border-ink/25 text-ink hover:border-ink/70")
                  }
                >
                  <input type="radio" name="storey" value={v}
                         checked={storey === v} onChange={() => setStorey(v)}
                         className="sr-only" />
                  <span className="font-display italic text-[17px] leading-none">
                    {v === "single" ? "Single-storey" : "Multi-storey"}
                  </span>
                  <span className="mt-1 block text-[11px] opacity-70">
                    {v === "single"
                      ? "One floor plan file"
                      : "One file per floor; add a stair"}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="flex flex-col gap-3">
            <legend className="caption">Material palette</legend>
            <div className="flex flex-col gap-2">
              {PRESETS.map((p) => (
                <label
                  key={p.id}
                  className={
                    "flex cursor-pointer items-center gap-3 border px-4 py-3 text-[14px] transition-standard duration-standard " +
                    (preset === p.id
                      ? "border-sienna/70 bg-sienna/[0.06]"
                      : "border-ink/15 hover:border-ink/35")
                  }
                >
                  <input
                    type="radio"
                    name="preset"
                    value={p.id}
                    checked={preset === p.id}
                    onChange={() => setPreset(p.id)}
                    className="sr-only"
                  />
                  <span
                    aria-hidden
                    className={
                      "block h-3 w-3 shrink-0 rounded-full border " +
                      (preset === p.id ? "border-sienna bg-sienna" : "border-ink/40")
                    }
                  />
                  <span className="text-ink/85">{p.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {err && <p className="text-[13px] text-sienna">{err}</p>}

          <div className="flex items-center justify-end gap-3 border-t border-ink/10 pt-6">
            <DialogClose asChild>
              <Button variant="ghost" type="button">Cancel</Button>
            </DialogClose>
            <Button type="submit" disabled={busy || !name.trim()}>
              {busy ? "Opening…" : "Open sheet"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
