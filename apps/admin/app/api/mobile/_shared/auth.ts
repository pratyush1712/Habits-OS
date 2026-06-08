import { NextResponse, type NextRequest } from "next/server";

/**
 * Optional shared-key protection for the native mobile companion.
 *
 * If HABITOS_MOBILE_API_KEY is configured on Vercel, the iOS app must send it
 * as X-HabitOS-Mobile-Key. If unset, routes stay open for quick personal use,
 * but only expose the narrow mobile surface below.
 */
export function rejectUnauthorizedMobileRequest(
  request: NextRequest,
): NextResponse | null {
  const expected = process.env.HABITOS_MOBILE_API_KEY?.trim();

  if (!expected) {
    return null;
  }

  const actual = request.headers.get("x-habitos-mobile-key")?.trim();

  if (actual === expected) {
    return null;
  }

  return NextResponse.json(
    { detail: "Missing or invalid mobile API key." },
    { status: 401 },
  );
}

export function jsonError(error: unknown): NextResponse {
  const message = error instanceof Error ? error.message : "Request failed.";

  return NextResponse.json({ detail: message }, { status: 502 });
}
