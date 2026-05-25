export type SearchParamsInput =
  | Promise<Record<string, string | string[] | undefined>>
  | Record<string, string | string[] | undefined>;

export type Notice = {
  message: string;
  tone: "error" | "info";
};

/**
 * Normalize App Router search params into plain strings.
 */
export async function resolveSearchParams(
  searchParams: SearchParamsInput | undefined,
): Promise<Record<string, string | undefined>> {
  const resolved = searchParams ? await searchParams : {};

  return Object.fromEntries(
    Object.entries(resolved).map(([key, value]) => [
      key,
      Array.isArray(value) ? value[0] : value,
    ]),
  );
}

/**
 * Pull a transient action notice out of the current search params.
 */
export async function readNotice(
  searchParams: SearchParamsInput | undefined,
): Promise<Notice | null> {
  const params = await resolveSearchParams(searchParams);
  const message = params.notice;

  if (!message) {
    return null;
  }

  return {
    message,
    tone: params.tone === "error" ? "error" : "info",
  };
}
