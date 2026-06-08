/**
 * Heavy divider used throughout the control-panel layout system.
 */
export function Rule({
  variant = "default",
}: {
  variant?: "default" | "soft" | "strong";
}) {
  const tone =
    variant === "strong"
      ? "border-slate-950"
      : variant === "soft"
        ? "border-slate-400"
        : "border-slate-950";

  return <hr className={`my-0 border-0 border-t-4 ${tone}`} />;
}
