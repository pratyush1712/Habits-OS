import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

import {
  AUTH_GUARDS_DISABLED,
  buildLoginRedirectPath,
  isAllowedAdminEmail,
  isPrivateAppPath,
  shouldUseSecureAuthCookie,
} from "@/lib/auth-access";

/**
 * Lightweight request-time auth gate for the private admin routes.
 */
export async function proxy(request: NextRequest) {
  if (AUTH_GUARDS_DISABLED) {
    return NextResponse.next();
  }

  const { pathname, search } = request.nextUrl;
  const token = await getToken({
    secureCookie: shouldUseSecureAuthCookie(request),
    req: request,
    secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  });
  const email = typeof token?.email === "string" ? token.email : null;
  const authenticated = isAllowedAdminEmail(email);

  if (pathname === "/login" && authenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (!isPrivateAppPath(pathname)) {
    return NextResponse.next();
  }

  if (!authenticated) {
    return NextResponse.redirect(
      new URL(buildLoginRedirectPath(pathname, search), request.url),
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
