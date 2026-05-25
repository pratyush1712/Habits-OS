import { JetBrains_Mono, Source_Serif_4 } from "next/font/google";

/**
 * Editorial serif used for all readable interface copy.
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
