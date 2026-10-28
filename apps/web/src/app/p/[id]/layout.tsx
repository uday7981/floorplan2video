import { TopBar } from "@/components/TopBar";
import { Stepper } from "@/components/Stepper";
import { MOCK_PROJECT } from "@/lib/mock-data";

/**
 * Shared layout for the entire project flow. In M7 the project is resolved
 * from the id param via the API; for M6 we use the mock.
 */
export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { id: string };
}) {
  const project = MOCK_PROJECT;
  return (
    <main className="relative z-10 flex min-h-screen flex-col">
      <TopBar
        spent={project.spent_usd}
        budget={project.budget_usd}
        rightSlot={
          <div className="flex items-center gap-3">
            <span className="caption">Project</span>
            <span className="font-display text-base italic text-ink/85">{project.name}</span>
          </div>
        }
      />
      <div className="border-b border-ink/10 bg-paper/60">
        <Stepper projectId={params.id} />
      </div>
      <div className="flex-1">{children}</div>
    </main>
  );
}
