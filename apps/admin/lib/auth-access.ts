/**
 * The admin app is intentionally single-user.
 * Only this Google account may access the private dashboard.
 */
export const ADMIN_EMAIL = "pratyushsudhakar03@gmail.com";

/**
 * Temporary polish mode bypass.
 * Flip this back to `false` once the UI pass is complete.
 */
export const AUTH_GUARDS_DISABLED = false;

/**
 * Public routes stay reachable without authentication.
 * Everything else in the app is treated as a private admin surface.
 */
const PUBLIC_PATH_PREFIXES = [
  "/api/auth",
  "/login",
];

/**
 * Normalize email comparisons so Google profile casing does not matter.
 */
function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

/**
 * Enforce a strict single-user allowlist for authenticated sessions.
 */
export function isAllowedAdminEmail(email: string | null | undefined): boolean {
  if (AUTH_GUARDS_DISABLED) {
    return true;
  }

  if (!email) {
    return false;
  }

  return normalizeEmail(email) === ADMIN_EMAIL;
}

/**
 * Private app routes match the pages documented in the setup guide.
 */
export function isPrivateAppPath(pathname: string): boolean {
  if (pathname === "/") {
    return false;
  }

  return !PUBLIC_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

/**
 * Preserve the user's original destination so login can return them there.
 */
export function buildLoginRedirectPath(
  pathname: string,
  search: string,
): string {
  const nextTarget = `${pathname}${search}`;
  const nextParam = encodeURIComponent(nextTarget);

  return `/login?next=${nextParam}`;
}
