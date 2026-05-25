import Link from "next/link";

import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { NoticeBanner } from "@/components/common/notice-banner";
import { Page } from "@/components/primitives/page";
import { Rule } from "@/components/primitives/rule";
import { isGoogleAuthConfigured } from "@/lib/auth";
import { readNotice, resolveSearchParams } from "@/lib/notice";

function mapAuthError(error: string | undefined): string | null {
  switch (error) {
    case "AccessDenied":
      return "The signed-in Google account is not allowed to access this admin surface.";
    case "Configuration":
      return "Google OAuth is not fully configured for the admin app yet.";
    default:
      return null;
  }
}

/**
 * Google-only sign-in surface for the single-user admin app.
 */
export default async function LoginPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await resolveSearchParams(searchParams);
  const notice = await readNotice(searchParams);
  const authError = mapAuthError(params.error);
  const callbackUrl = params.next ?? "/dashboard";

  return (
    <div className="min-h-screen bg-paper">
      <Page className="py-16 md:py-24">
        <div className="mx-auto max-w-[760px] space-y-8">
          <div className="space-y-5 border-b border-ink pb-8">
            <p className="mono-label m-0">Sign in</p>
            <h1 className="m-0 text-[clamp(2.5rem,6vw,5rem)] leading-[0.98] tracking-[-0.03em] font-light">
              Google only. One operator.
            </h1>
            <p className="section-lede m-0">
              Authentication is intentionally minimal: a single Google account,
              a single private surface, and no local passwords to maintain.
            </p>
          </div>

          {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}
          {authError ? <NoticeBanner tone="error">{authError}</NoticeBanner> : null}

          <section className="paper-panel px-6 py-6">
            <div className="space-y-4">
              <p className="mono-label m-0">Access policy</p>
              <Rule />
              <p className="m-0 body-column">
                Only <code>pratyushsudhakar03@gmail.com</code> is accepted. If
                Google OAuth is not configured on this deployment yet, the sign-in
                button stays disabled instead of failing mysteriously.
              </p>
              <div className="flex flex-wrap gap-4 pt-2">
                <GoogleSignInButton
                  callbackUrl={callbackUrl}
                  enabled={isGoogleAuthConfigured}
                />
                <Link className="muted-link inline-flex items-center" href="/">
                  Back to overview
                </Link>
              </div>
            </div>
          </section>
        </div>
      </Page>
    </div>
  );
}
