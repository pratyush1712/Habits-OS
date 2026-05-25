import "server-only";

import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import type { NextAuthOptions, Session } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

import { AUTH_GUARDS_DISABLED, isAllowedAdminEmail } from "./auth-access";

const googleClientId =
  process.env.AUTH_GOOGLE_ID ?? process.env.GOOGLE_CLIENT_ID ?? "";
const googleClientSecret =
  process.env.AUTH_GOOGLE_SECRET ?? process.env.GOOGLE_CLIENT_SECRET ?? "";

/**
 * Session shape after the single-user allowlist has been enforced.
 */
export type AdminSession = Session & {
  user: NonNullable<Session["user"]> & {
    email: string;
  };
};

/**
 * Server-safe flag for conditionally rendering the Google sign-in button.
 */
export const isGoogleAuthConfigured =
  googleClientId.length > 0 && googleClientSecret.length > 0;

/**
 * NextAuth configuration for the private admin surface.
 */
export const authOptions: NextAuthOptions = {
  secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  providers: isGoogleAuthConfigured
    ? [
        GoogleProvider({
          clientId: googleClientId,
          clientSecret: googleClientSecret,
        }),
      ]
    : [],
  callbacks: {
    /**
     * Reject any Google account that is not the single configured admin.
     */
    async signIn({ user }) {
      if (!isAllowedAdminEmail(user.email)) {
        return "/login?error=AccessDenied";
      }

      return true;
    },

    /**
     * Keep the email claim on the JWT so Proxy can gate routes quickly.
     */
    async jwt({ token, user }) {
      if (typeof user?.email === "string") {
        token.email = user.email;
      }

      return token;
    },

    /**
     * Preserve the email on the session payload for server-rendered pages.
     */
    async session({ session, token }) {
      if (session.user && typeof token.email === "string") {
        session.user.email = token.email;
      }

      return session;
    },
  },
};

/**
 * Narrow an arbitrary NextAuth session into the single-user admin session.
 */
function toAdminSession(session: Session | null): AdminSession | null {
  if (AUTH_GUARDS_DISABLED) {
    return {
      expires: new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString(),
      user: {
        email: "polish-mode@local",
        image: null,
        name: "Polish Mode",
      },
    };
  }

  if (!session?.user?.email) {
    return null;
  }

  if (!isAllowedAdminEmail(session.user.email)) {
    return null;
  }

  return {
    ...session,
    user: {
      ...session.user,
      email: session.user.email,
    },
  };
}

/**
 * Read the current authenticated admin session on the server.
 */
export async function getAdminSession(): Promise<AdminSession | null> {
  const session = await getServerSession(authOptions);

  return toAdminSession(session);
}

/**
 * Require an authenticated admin session before rendering a private route.
 */
export async function requireAdminSession(): Promise<AdminSession> {
  const session = await getAdminSession();

  if (!session) {
    redirect("/login");
  }

  return session;
}
