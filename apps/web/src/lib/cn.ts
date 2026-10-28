import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tiny classnames helper used by every component. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
