import { Inter, Instrument_Serif, JetBrains_Mono } from "next/font/google";

/**
 * next/font bundles + subsets + size-adjust-overrides the fonts at build time,
 * eliminating CLS. Combined with the `.font-gate` opacity trick in globals.css,
 * display text never flashes a fallback — the whole non-negotiable from
 * design-thinking.
 */

export const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const display = Instrument_Serif({
  weight: ["400"],
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-display",
  display: "block",   // the hero face: hold invisible until it's really ready
});

export const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});
