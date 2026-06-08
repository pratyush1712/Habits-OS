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

type AuthCookieRequestShape = {
  cookies: {
    getAll(): Array<{
      name: string;
      value: string;
    }>;
  };
  headers: {
    get(name: string): string | null;
  };
  nextUrl: {
    protocol: string;
  };
};

/**
 * Public routes stay reachable without authentication.
 * Everything else in the app is treated as a private admin surface.
 */
const PUBLIC_PATH_PREFIXES = [
  "/api/auth",
  "/api/mobile",
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

/**
 * Match NextAuth's secure cookie naming on HTTPS production deployments,
 * even when `NEXTAUTH_URL` or `VERCEL` are not set.
 */
export function shouldUseSecureAuthCookie(
  request: AuthCookieRequestShape,
): boolean {
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const normalizedForwardedProto = forwardedProto
    ?.split(",")[0]
    ?.trim()
    .toLowerCase();

  if (normalizedForwardedProto === "https") {
    return true;
  }

  if (request.nextUrl.protocol === "https:") {
    return true;
  }

  return request.cookies
    .getAll()
    .some(({ name }) => name.startsWith("__Secure-next-auth.session-token"));
}
