/**
 * Hairline rule used throughout the editorial layout system.
 */
export function Rule({
  variant = "default",
}: {
  variant?: "default" | "soft" | "strong";
}) {
  const tone =
    variant === "strong"
      ? "border-ink"
      : variant === "soft"
        ? "border-rule-soft"
        : "border-rule";

  return <hr className={`my-0 border-0 border-t ${tone}`} />;
}
