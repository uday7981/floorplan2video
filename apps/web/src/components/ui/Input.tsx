"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, hint, id, className, ...rest }, ref) {
    const generatedId = React.useId();
    const inputId = id ?? generatedId;
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="caption">
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            "h-11 w-full bg-transparent px-0 pb-2 text-[15px] text-ink",
            "border-b border-ink/25 outline-none transition-standard duration-standard",
            "focus:border-ink placeholder:text-ink/35",
            className,
          )}
          {...rest}
        />
        {hint && <p className="text-[12px] text-ink/50">{hint}</p>}
      </div>
    );
  },
);
