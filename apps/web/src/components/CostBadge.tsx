import { cn } from "@/lib/cn";

/**
 * A tiny spend-vs-budget gauge. Reads as an architect's dimension-string on
 * the right side of the top bar. Dialled sienna when ≥ 80% spent.
 */
export function CostBadge({
  spent,
  budget,
  className,
}: {
  spent: number;
  budget: number;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(1, budget > 0 ? spent / budget : 0));
  const warn = pct >= 0.8;
  const barColor = warn ? "rgb(var(--sienna))" : "rgb(var(--ink))";
  return (
    <div className={cn("flex items-center gap-2 text-sm sm:gap-3", className)}>
      <span className="caption shrink-0 hidden sm:inline">Spend</span>
      <div className="relative h-[6px] w-[56px] shrink-0 overflow-hidden rounded-full sm:w-[88px]">
        <div className="absolute inset-0" style={{ background: "rgb(var(--ink) / 0.1)" }} />
        <div
          className="absolute inset-y-0 left-0 transition-standard duration-standard"
          style={{ width: `${pct * 100}%`, background: barColor }}
        />
      </div>
      <span
        className={cn(
          "mono-num text-[12px] tracking-tight tabular-nums",
          warn && "text-sienna",
        )}
      >
        <span className="text-ink/90">${spent.toFixed(2)}</span>
        <span className="text-ink/35"> / ${budget.toFixed(0)}</span>
      </span>
    </div>
  );
}
