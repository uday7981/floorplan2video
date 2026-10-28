import { BrandMark } from "./BrandMark";
import { CostBadge } from "./CostBadge";

/**
 * Top bar: brand mark on the left, project meta + cost on the right.
 * Flex-wraps gracefully so a 390px viewport doesn't horizontally scroll.
 */
export function TopBar({
  spent,
  budget,
  rightSlot,
}: {
  spent?: number;
  budget?: number;
  rightSlot?: React.ReactNode;
}) {
  return (
    <header className="relative z-10 border-b border-ink/10 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-page flex-wrap items-center gap-x-6 gap-y-3 px-6 md:px-sheet py-5">
        <BrandMark />
        <div className="ml-auto flex flex-wrap items-center gap-x-6 gap-y-3">
          {rightSlot}
          {typeof spent === "number" && typeof budget === "number" && (
            <CostBadge spent={spent} budget={budget} />
          )}
        </div>
      </div>
    </header>
  );
}
