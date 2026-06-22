import { NextRequest, NextResponse } from "next/server";

import { api } from "@/lib/api-client";

import { jsonError, rejectUnauthorizedMobileRequest } from "../../_shared/auth";

export const runtime = "nodejs";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const unauthorized = rejectUnauthorizedMobileRequest(request);

  if (unauthorized) {
    return unauthorized;
  }

  try {
    const payload = await request.json();

    return NextResponse.json(await api.logProteinShake(payload));
  } catch (error) {
    return jsonError(error);
  }
}
