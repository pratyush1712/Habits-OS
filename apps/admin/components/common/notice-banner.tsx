import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Persistent inline banner for action results and auth errors.
 */
export function NoticeBanner({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "error" | "info";
}) {
  return (
    <div
      className={cn(
        "notice-banner",
        tone === "error" ? "notice-banner-error" : "notice-banner-info",
      )}
    >
      {children}
    </div>
  );
}
