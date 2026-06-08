import { JetBrains_Mono, Source_Serif_4 } from "next/font/google";

/**
 * Legacy serif export kept for compatibility; the admin UI now uses a plain system sans.
 */
export const serif = Source_Serif_4({
  subsets: ["latin"],
  weight: "variable",
  axes: ["opsz"],
  variable: "--font-serif-loaded",
  display: "swap",
  fallback: ["Georgia", "Times New Roman", "serif"],
});

/**
 * Monospace face for numbers, timestamps, and identifiers.
 */
export const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono-loaded",
  display: "swap",
  fallback: ["ui-monospace", "Menlo", "monospace"],
});
