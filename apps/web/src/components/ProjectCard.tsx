import Link from "next/link";
import type { Project } from "@/lib/types";
import { cn } from "@/lib/cn";

const STATUS_LABEL: Record<Project["status"], string> = {
  draft:            "Draft",
  plan_review:      "Plan review",
  journey:          "Journey",
  boundary_frames:  "Boundary frames",
  rendering:        "Rendering",
  video:            "Generating video",
  exported:         "Exported",
};

/**
 * One architect's plan sheet per project. Serif project name, caption-rail
 * meta on the right (status + spend/budget), a sheet-number stamp top-left.
 */
export function ProjectCard({ project, index }: { project: Project; index: number }) {
  const pct = project.budget_usd > 0 ? project.spent_usd / project.budget_usd : 0;
  return (
    <Link
      href={`/p/${project.id}/upload`}
      className={cn(
        "group relative block overflow-hidden border border-ink/15 bg-paper",
        "transition-standard duration-standard hover:border-ink/50",
      )}
    >
      {/* sheet number stamp */}
      <span className="absolute left-6 top-6 caption text-ink/40">
        Sheet {String(index + 1).padStart(2, "0")}
      </span>

      {/* trace-line grid in the top band — just enough to feel like plan paper */}
      <div
        aria-hidden
        className="h-28 border-b border-ink/10 bg-paper-dim"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, rgba(31,58,95,0.05) 0 1px, transparent 1px 24px), " +
            "repeating-linear-gradient(90deg, rgba(31,58,95,0.05) 0 1px, transparent 1px 24px)",
        }}
      />

      <div className="flex flex-col gap-5 p-6">
        <div className="flex flex-col gap-2">
          <h2 className="font-display text-[26px] leading-[1.05] tracking-display text-ink group-hover:italic">
            {project.name}
          </h2>
          <div className="flex items-center gap-2 text-[12px] text-ink/55">
            <span className="caption text-ink/55">{project.project_type}</span>
            <span className="h-[3px] w-[3px] rounded-full bg-ink/30" />
            <span>{STATUS_LABEL[project.status]}</span>
          </div>
        </div>

        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <span className="caption text-ink/55">Spend</span>
            <span className="mono-num text-[16px] text-ink/90">
              ${project.spent_usd.toFixed(2)}
              <span className="text-ink/35"> / ${project.budget_usd.toFixed(0)}</span>
            </span>
          </div>
          <div className="relative h-1 w-24 overflow-hidden">
            <div className="absolute inset-0 bg-ink/10" />
            <div
              className="absolute inset-y-0 left-0 bg-ink transition-standard duration-standard"
              style={{ width: `${Math.min(1, pct) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </Link>
  );
}
