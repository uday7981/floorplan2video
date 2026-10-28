"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 font-sans font-medium whitespace-nowrap " +
  "transition-standard duration-standard disabled:opacity-40 disabled:cursor-not-allowed " +
  "select-none";

const sizes: Record<Size, string> = {
  sm: "h-8  px-3   text-[13px] rounded-[2px]",
  md: "h-10 px-4   text-[14px] rounded-[2px]",
  lg: "h-12 px-6   text-[15px] rounded-[2px]",
};

const variants: Record<Variant, string> = {
  primary:
    "bg-ink text-paper hover:bg-sienna active:bg-sienna/90",
  secondary:
    "bg-transparent text-ink border border-ink/25 hover:border-ink/70",
  ghost:
    "bg-transparent text-ink/70 hover:text-ink",
  danger:
    "bg-transparent text-sienna border border-sienna/40 hover:bg-sienna hover:text-paper",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { variant = "primary", size = "md", asChild, className, ...rest },
    ref,
  ) {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref as any}
        className={cn(base, sizes[size], variants[variant], className)}
        {...rest}
      />
    );
  },
);
