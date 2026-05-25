import type { HabitEntry } from "@/lib/api-client";
import { formatSourceLabel, formatStatusLabel } from "@/lib/formatters";

import { Numeric } from "../primitives/numeric";
import { StatusGlyph } from "../primitives/status-glyph";

/**
 * Habit entry explanation block used on day and habit detail pages.
 */
export function RuleExplanation({
  entry,
}: {
  entry: HabitEntry;
}) {
  const glyphKind =
    entry.status === "checked" || entry.status === "manual"
      ? "complete"
      : entry.status === "partial"
        ? "partial"
        : entry.status === "warning"
          ? "anomaly"
          : "empty";

  return (
    <article className="space-y-3 border-b border-rule py-4 last:border-b-0">
      <div className="flex flex-wrap items-center gap-3">
        <StatusGlyph kind={glyphKind} size={14} />
        <h3 className="m-0 text-[18px] font-medium">
          {formatStatusLabel(entry.status)}
        </h3>
        <span className="status-note">{formatSourceLabel(entry.source)}</span>
        {entry.manually_overridden ? (
          <span className="status-note-strong">Override</span>
        ) : null}
      </div>
      <p className="m-0 body-column text-ink-mid">
        {entry.summary || "No summary was provided."}
      </p>
      <p className="m-0 body-column">
        {entry.explanation || entry.description || "No explanation was provided."}
      </p>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        <Numeric unit="confidence" value={entry.confidence.toFixed(2)} />
        <Numeric
          unit="linked events"
          value={entry.linked_source_event_ids?.length ?? 0}
        />
      </div>
    </article>
  );
}
