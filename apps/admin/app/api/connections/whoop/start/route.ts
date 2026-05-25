import { redirect } from "next/navigation";

import { api } from "@/lib/api-client";
import { asRecord, readString } from "@/lib/data-helpers";

/**
 * Server-side OAuth bootstrap so the browser never talks directly to FastAPI.
 */
export async function GET(): Promise<Response> {
  const payload = await api.whoopOAuthStart();
  const authorizationUrl = readString(asRecord(payload), "authorization_url");

  if (!authorizationUrl) {
    redirect("/connections?notice=WHOOP%20OAuth%20start%20failed.&tone=error");
  }

  redirect(authorizationUrl);
}
