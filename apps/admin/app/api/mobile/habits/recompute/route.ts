import { type NextRequest, NextResponse } from "next/server";

import { api } from "@/lib/api-client";

import { jsonError, rejectUnauthorizedMobileRequest } from "../../_shared/auth";

export const runtime = "nodejs";

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export async function POST(request: NextRequest): Promise<NextResponse> {
  const unauthorized = rejectUnauthorizedMobileRequest(request);

  if (unauthorized) {
    return unauthorized;
  }

  const month = request.nextUrl.searchParams.get("month") ?? "";

  if (!MONTH_PATTERN.test(month)) {
    return NextResponse.json(
      { detail: "month must be YYYY-MM." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await api.recompute(month));
  } catch (error) {
    return jsonError(error);
  }
}
