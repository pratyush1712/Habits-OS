import { type NextRequest, NextResponse } from "next/server";

import { api } from "@/lib/api-client";

import { jsonError, rejectUnauthorizedMobileRequest } from "../_shared/auth";

export const runtime = "nodejs";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const unauthorized = rejectUnauthorizedMobileRequest(request);

  if (unauthorized) {
    return unauthorized;
  }

  try {
    return NextResponse.json(await api.health());
  } catch (error) {
    return jsonError(error);
  }
}
