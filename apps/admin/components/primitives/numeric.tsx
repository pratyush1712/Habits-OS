import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Monospace numeric readout with optional serif unit annotation.
 */
export function Numeric({
  className,
  unit,
  value,
}: {
  className?: string;
  unit?: ReactNode;
  value: ReactNode;
}) {
  return (
    <span className={cn("tabular font-mono text-[14px] text-ink", className)}>
      {value}
      {unit ? <span className="ml-1 font-serif italic text-ink-mid">{unit}</span> : null}
    </span>
  );
}
