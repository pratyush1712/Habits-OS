import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Monospace numeric readout with optional unit annotation.
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
    <span className={cn("tabular font-mono text-[15px] font-black text-slate-950", className)}>
      {value}
      {unit ? <span className="ml-1 font-sans text-slate-700">{unit}</span> : null}
    </span>
  );
}
