import { cn } from "@/lib/utils";

export type StatusKind = "complete" | "partial" | "anomaly" | "empty" | "na";

const LABELS: Record<StatusKind, string> = {
  anomaly: "Anomaly",
  complete: "Complete",
  empty: "Empty",
  na: "Not applicable",
  partial: "Partial",
};

/**
 * Controlled SVG glyphs that mirror the PDF vocabulary without font drift.
 */
export function StatusGlyph({
  className,
  kind,
  size = 14,
}: {
  className?: string;
  kind: StatusKind;
  size?: number;
}) {
  const stroke = size < 14 ? 1.5 : 1.25;
  const tone = kind === "anomaly" ? "text-anomaly" : "text-current";

  return (
    <svg
      aria-label={LABELS[kind]}
      className={cn("inline-block shrink-0 align-[-0.125em]", tone, className)}
      height={size}
      role="img"
      viewBox="0 0 16 16"
      width={size}
    >
      {kind === "complete" ? (
        <circle cx="8" cy="8" fill="currentColor" r="5" />
      ) : null}
      {kind === "partial" ? (
        <>
          <circle
            cx="8"
            cy="8"
            fill="none"
            r="5"
            stroke="currentColor"
            strokeWidth={stroke}
          />
          <path d="M8 3 A 5 5 0 0 1 8 13 Z" fill="currentColor" />
        </>
      ) : null}
      {kind === "anomaly" ? (
        <path
          d="M8 2.5 L13.5 12.5 L2.5 12.5 Z"
          fill="none"
          stroke="currentColor"
          strokeLinejoin="miter"
          strokeWidth={stroke + 0.15}
        />
      ) : null}
      {kind === "empty" ? (
        <circle
          cx="8"
          cy="8"
          fill="none"
          r="5"
          stroke="currentColor"
          strokeWidth={stroke}
        />
      ) : null}
      {kind === "na" ? (
        <path
          d="M4 8 L12 8"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth={stroke}
        />
      ) : null}
    </svg>
  );
}
