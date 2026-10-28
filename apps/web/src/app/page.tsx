"use client";

import * as React from "react";
import { TopBar } from "@/components/TopBar";
import { ProjectCard } from "@/components/ProjectCard";
import { NewProjectDialog } from "@/components/NewProjectDialog";
import { Hairline } from "@/components/ui/Hairline";
import type { Project } from "@/lib/types";

/**
 * Mock projects for the design pass. In M6-Phase-B these come from
 * api.projects.list(authToken). The shape matches apps/api's response.
 */
const MOCK: Project[] = [
  {
    id: "oakhill",
    name: "Oakhill Residence",
    project_type: "house",
    style_preset: { materials: "oak, black aluminium, natural white" },
    budget_usd: 40,
    spent_usd: 8.19,
    status: "video",
  },
  {
    id: "studio",
    name: "North Studio",
    project_type: "interior",
    style_preset: { materials: "concrete, steel, white" },
    budget_usd: 40,
    spent_usd: 1.84,
    status: "plan_review",
  },
  {
    id: "cliff",
    name: "Cliffside Pavilion",
    project_type: "house",
    style_preset: { materials: "walnut, aluminium, charcoal" },
    budget_usd: 60,
    spent_usd: 32.11,
    status: "exported",
  },
];

export default function Home() {
  const [projects, setProjects] = React.useState<Project[]>(MOCK);

  const totalSpent = projects.reduce((s, p) => s + p.spent_usd, 0);
  const totalBudget = projects.reduce((s, p) => s + p.budget_usd, 0);

  return (
    <main className="relative z-10 min-h-screen">
      <TopBar spent={totalSpent} budget={totalBudget} />

      {/* Hero: single oversized title with the drafter's byline underneath. */}
      <section className="mx-auto max-w-page px-6 md:px-sheet pb-16 pt-24 md:pt-32">
        <div className="grid grid-cols-12 gap-x-6">
          <div className="col-span-12 md:col-span-9">
            <span className="caption text-ink/55">The drafter · 2026</span>
            <h1 className="font-gate mt-6 font-display text-[clamp(44px,8vw,92px)] leading-[0.98] tracking-display">
              Plans in,
              <br />
              <span className="italic text-sienna">walkthroughs</span> out.
            </h1>
            <p className="mt-8 max-w-[52ch] text-[16px] leading-[1.65] text-ink/70">
              Upload a floor plan. Review the extracted geometry. Approve a few
              frames. One hour later, you have a 30–60 second architectural
              walkthrough video — rendered end-to-end for under $35.
            </p>
          </div>
          <aside className="col-span-12 mt-8 flex items-start justify-start md:col-span-3 md:mt-0 md:justify-end">
            <NewProjectDialog
              onCreate={async (body) => {
                // Mock implementation for M6-Phase-A — swap for api.projects.create
                // once Supabase auth lands and apps/api is reachable from the browser.
                const created: Project = {
                  id: Math.random().toString(36).slice(2, 10),
                  name: body.name,
                  project_type: body.project_type,
                  style_preset: body.style_preset,
                  budget_usd: 40,
                  spent_usd: 0,
                  status: "draft",
                };
                setProjects((prev) => [created, ...prev]);
                return created;
              }}
            />
          </aside>
        </div>
      </section>

      <Hairline />

      {/* Projects grid */}
      <section className="mx-auto max-w-page px-6 md:px-sheet py-16">
        <header className="mb-10 flex flex-wrap items-end justify-between gap-6">
          <div className="flex flex-col gap-2">
            <span className="caption">Projects</span>
            <h2 className="font-display text-[32px] leading-tight tracking-display">
              <span className="mono-num text-[18px] text-ink/40 align-middle mr-3">
                {String(projects.length).padStart(2, "0")}
              </span>
              on your drafting table
            </h2>
          </div>
        </header>

        {projects.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((p, i) => (
              <ProjectCard key={p.id} project={p} index={i} />
            ))}
          </div>
        )}
      </section>

      <footer className="mt-24 border-t border-ink/10">
        <div className="mx-auto max-w-page px-6 md:px-sheet py-10 flex flex-wrap items-center justify-between gap-4 text-[12px] text-ink/50">
          <span className="caption">v0.1 — MVP</span>
          <span className="font-display italic">— the drafter</span>
        </div>
      </footer>
    </main>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-start gap-4 border border-dashed border-ink/20 bg-paper-dim/40 p-12">
      <span className="caption">A blank sheet</span>
      <h3 className="font-display italic text-[26px] leading-tight">
        Nothing drafted yet.
      </h3>
      <p className="max-w-[46ch] text-[14px] text-ink/65">
        Start a new project to upload a floor plan and generate your first walkthrough.
      </p>
    </div>
  );
}
