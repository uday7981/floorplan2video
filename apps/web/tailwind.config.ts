import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Semantic tokens — map to CSS vars so a theme swap is one line later.
        paper:      "rgb(var(--paper) / <alpha-value>)",
        "paper-dim":"rgb(var(--paper-dim) / <alpha-value>)",
        ink:        "rgb(var(--ink) / <alpha-value>)",
        sienna:     "rgb(var(--sienna) / <alpha-value>)",
        trace:      "rgb(var(--trace) / <alpha-value>)",
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
        sans:    ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono:    ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      // 4-based spacing. Tailwind already does this; adding named "sheet" + "gutter" aliases.
      spacing: {
        gutter: "24px",
        sheet:  "48px",
      },
      // Signature easing — "expo-ish". Used wherever `transition-standard` is applied.
      transitionTimingFunction: {
        standard: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      },
      transitionDuration: {
        micro: "160ms",
        standard: "240ms",
        reveal: "800ms",
      },
      maxWidth: {
        page: "1440px",
      },
      letterSpacing: {
        caption: "0.08em",
        display: "-0.02em",
      },
      borderColor: {
        DEFAULT: "rgb(var(--ink) / 0.15)",
      },
    },
  },
  plugins: [],
};

export default config;
