"use client";

import * as React from "react";
import * as Primitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

export const Dialog = Primitive.Root;
export const DialogTrigger = Primitive.Trigger;
export const DialogClose = Primitive.Close;

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof Primitive.Content>,
  React.ComponentPropsWithoutRef<typeof Primitive.Content> & { title: string; description?: string }
>(function DialogContent({ className, children, title, description, ...rest }, ref) {
  return (
    <Primitive.Portal>
      <Primitive.Overlay className="fixed inset-0 z-40 bg-ink/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <Primitive.Content
        ref={ref}
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-[min(560px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2",
          "bg-paper border border-ink/15 shadow-[0_30px_80px_-30px_rgba(20,19,17,0.3)]",
          "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
          className,
        )}
        {...rest}
      >
        <div className="flex items-start justify-between gap-6 border-b border-ink/10 px-8 pt-8 pb-6">
          <div className="flex flex-col gap-2">
            <span className="caption">New file</span>
            <Primitive.Title className="font-display text-[28px] leading-[1.1] tracking-display">
              {title}
            </Primitive.Title>
            {description && (
              <Primitive.Description className="text-[14px] text-ink/60 max-w-[46ch]">
                {description}
              </Primitive.Description>
            )}
          </div>
          <Primitive.Close
            className="rounded-sm p-1 text-ink/50 transition-standard duration-standard hover:text-ink"
            aria-label="Close"
          >
            <X size={18} strokeWidth={1.5} />
          </Primitive.Close>
        </div>
        <div className="px-8 py-8">{children}</div>
      </Primitive.Content>
    </Primitive.Portal>
  );
});
