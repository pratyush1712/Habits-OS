import { describe, expect, it } from "vitest";

import {
  ADMIN_EMAIL,
  buildLoginRedirectPath,
  isAllowedAdminEmail,
  isPrivateAppPath,
  shouldUseSecureAuthCookie,
} from "./auth-access";

describe("auth access controls", () => {
  it("allows only the configured admin email", () => {
    expect(isAllowedAdminEmail(ADMIN_EMAIL)).toBe(true);
    expect(isAllowedAdminEmail("PratyushSudhakar03@Gmail.com")).toBe(true);
    expect(isAllowedAdminEmail("someone@example.com")).toBe(false);
    expect(isAllowedAdminEmail(null)).toBe(false);
  });

  it("treats the documented admin screens as private routes", () => {
    expect(isPrivateAppPath("/")).toBe(false);
    expect(isPrivateAppPath("/login")).toBe(false);
    expect(isPrivateAppPath("/api/auth/session")).toBe(false);
    expect(isPrivateAppPath("/month/2026-05")).toBe(true);
    expect(isPrivateAppPath("/events")).toBe(true);
    expect(isPrivateAppPath("/settings")).toBe(true);
  });

  it("preserves the original destination when redirecting to login", () => {
    expect(buildLoginRedirectPath("/events", "?month=2026-05")).toBe(
      "/login?next=%2Fevents%3Fmonth%3D2026-05",
    );
    expect(buildLoginRedirectPath("/settings", "")).toBe(
      "/login?next=%2Fsettings",
    );
  });

  it("uses secure auth cookies for forwarded https requests", () => {
    expect(
      shouldUseSecureAuthCookie({
        cookies: {
          getAll: () => [],
        },
        headers: {
          get: (name) => (name === "x-forwarded-proto" ? "https" : null),
        },
        nextUrl: {
          protocol: "http:",
        },
      }),
    ).toBe(true);
  });

  it("falls back to secure cookie detection when the secure cookie already exists", () => {
    expect(
      shouldUseSecureAuthCookie({
        cookies: {
          getAll: () => [
            {
              name: "__Secure-next-auth.session-token",
              value: "token",
            },
          ],
        },
        headers: {
          get: () => null,
        },
        nextUrl: {
          protocol: "http:",
        },
      }),
    ).toBe(true);
  });

  it("keeps local http requests on the non-secure cookie path", () => {
    expect(
      shouldUseSecureAuthCookie({
        cookies: {
          getAll: () => [],
        },
        headers: {
          get: () => null,
        },
        nextUrl: {
          protocol: "http:",
        },
      }),
    ).toBe(false);
  });
});
