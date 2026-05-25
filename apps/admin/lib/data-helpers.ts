/**
 * Safely narrow unknown JSON payloads into records for dashboard summaries.
 */
export function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

/**
 * Read a string property from a loose API response object.
 */
export function readString(
  record: Record<string, unknown> | null,
  key: string,
): string | null {
  if (!record) {
    return null;
  }

  const value = record[key];

  return typeof value === "string" ? value : null;
}

/**
 * Read a boolean property from a loose API response object.
 */
export function readBoolean(
  record: Record<string, unknown> | null,
  key: string,
): boolean | null {
  if (!record) {
    return null;
  }

  const value = record[key];

  return typeof value === "boolean" ? value : null;
}

/**
 * Narrow a loose property into an array.
 */
export function readArray(
  record: Record<string, unknown> | null,
  key: string,
): unknown[] {
  if (!record) {
    return [];
  }

  const value = record[key];

  return Array.isArray(value) ? value : [];
}
