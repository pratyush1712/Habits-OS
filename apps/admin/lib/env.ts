import "server-only";

import { ADMIN_EMAIL } from "./auth-access";

/**
 * Resolve the API base URL without exposing secrets in the UI.
 */
function resolveApiBaseUrl(): string {
  return process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
}

/**
 * Safely derive a host label for settings and diagnostics screens.
 */
function resolveApiHost(baseUrl: string): string {
  try {
    return new URL(baseUrl).host;
  } catch {
    return "invalid-url";
  }
}

/**
 * Shared server-only configuration flags used by the admin UI.
 */
export const serverRuntimeConfig = {
  adminEmail: ADMIN_EMAIL,
  apiBaseUrl: resolveApiBaseUrl(),
  apiHost: resolveApiHost(resolveApiBaseUrl()),
  apiAdminKeyConfigured: Boolean(process.env.API_ADMIN_KEY),
  authSecretConfigured: Boolean(
    process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  ),
  googleAuthConfigured: Boolean(
    (process.env.AUTH_GOOGLE_ID ?? process.env.GOOGLE_CLIENT_ID) &&
      (process.env.AUTH_GOOGLE_SECRET ?? process.env.GOOGLE_CLIENT_SECRET),
  ),
};
