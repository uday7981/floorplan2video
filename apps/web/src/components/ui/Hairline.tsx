import { cn } from "@/lib/cn";

/** 1px drafting line. Omit the orientation prop for a block divider. */
export function Hairline({
  className,
  vertical,
}: {
  className?: string;
  vertical?: boolean;
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "bg-ink/15",
        vertical ? "w-px self-stretch" : "h-px w-full",
        className,
      )}
    />
  );
}
