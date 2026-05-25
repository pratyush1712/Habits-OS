import { PageHeader, Section } from "@/components/primitives/page";
import { serverRuntimeConfig } from "@/lib/env";

/**
 * Safe configuration overview that avoids printing secrets while still making
 * deployment posture obvious.
 */
export default function SettingsPage() {
  return (
    <div className="space-y-16">
      <PageHeader
        eyebrow="Settings"
        subtitle="Only safe deployment metadata is shown here. Secrets stay server-side."
        title="Deployment posture"
      />

      <Section
        kicker="Runtime"
        lede="This screen intentionally reports booleans and hosts, never credentials."
        number="01"
        title="Server-side configuration"
      >
        <div className="data-column grid gap-4 md:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Allowed admin email</p>
            <p className="mt-4 mb-0">{serverRuntimeConfig.adminEmail}</p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">API host</p>
            <p className="mt-4 mb-0">{serverRuntimeConfig.apiHost}</p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Google OAuth</p>
            <p className="mt-4 mb-0">
              {serverRuntimeConfig.googleAuthConfigured
                ? "Configured"
                : "Missing client id or secret"}
            </p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Backend admin key</p>
            <p className="mt-4 mb-0">
              {serverRuntimeConfig.apiAdminKeyConfigured
                ? "Configured"
                : "Not configured"}
            </p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Session secret</p>
            <p className="mt-4 mb-0">
              {serverRuntimeConfig.authSecretConfigured
                ? "Configured"
                : "Missing AUTH_SECRET / NEXTAUTH_SECRET"}
            </p>
          </section>
        </div>
      </Section>
    </div>
  );
}
