import {
  format,
  formatDistanceToNow,
  isValid,
  parse,
  parseISO,
  startOfMonth,
} from "date-fns";

import type { HabitEntry, SourceEvent } from "./api-client";

export type GlyphKind = "complete" | "partial" | "anomaly" | "empty" | "na";

/**
 * Human-readable month title for navigation and page headings.
 */
export function formatMonthLabel(month: string): string {
  const parsed = parse(month, "yyyy-MM", startOfMonth(new Date()));

  return isValid(parsed) ? format(parsed, "MMMM yyyy") : month;
}

/**
 * Human-readable date title for day detail pages.
 */
export function formatDateLabel(date: string): string {
  const parsed = parseISO(date);

  return isValid(parsed) ? format(parsed, "EEEE, MMMM d, yyyy") : date;
}

/**
 * Compact timestamp label used across operational summaries.
 */
export function formatDateTimeLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  const parsed = parseISO(value);

  return isValid(parsed) ? format(parsed, "MMM d, yyyy 'at' HH:mm") : value;
}

/**
 * Relative timestamp for the small metadata strips in the shell.
 */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return "Never";
  }

  const parsed = parseISO(value);

  return isValid(parsed)
    ? formatDistanceToNow(parsed, { addSuffix: true })
    : value;
}

/**
 * Convert internal source ids into quiet UI labels.
 */
export function formatSourceLabel(source: string): string {
  return source
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/**
 * Convert internal status ids into UI labels.
 */
export function formatStatusLabel(status: HabitEntry["status"]): string {
  switch (status) {
    case "checked":
      return "Checked";
    case "partial":
      return "Partial";
    case "warning":
      return "Warning";
    case "missed":
      return "Missed";
    case "manual":
      return "Manual";
    default:
      return status;
  }
}

/**
 * Translate habit entry status into the controlled glyph vocabulary.
 */
export function mapEntryStatusToGlyph(
  status: HabitEntry["status"],
): GlyphKind {
  switch (status) {
    case "checked":
    case "manual":
      return "complete";
    case "partial":
      return "partial";
    case "warning":
      return "anomaly";
    case "missed":
      return "empty";
    default:
      return "na";
  }
}

/**
 * Apply the paper/ink palette consistently to status-driven text.
 */
export function statusToneClass(status: HabitEntry["status"]): string {
  switch (status) {
    case "warning":
      return "text-anomaly";
    case "missed":
      return "text-ink-ghost";
    default:
      return "text-ink";
  }
}

/**
 * Extract a useful minutes label from a normalized source event.
 */
export function formatEventDuration(event: SourceEvent): string | null {
  const minutes = event.metrics?.duration_minutes;

  if (typeof minutes === "number") {
    return `${minutes.toFixed(0)} min`;
  }

  return null;
}
