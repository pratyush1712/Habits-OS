import Link from "next/link";

import { Page, Section } from "@/components/primitives/page";
import { Rule } from "@/components/primitives/rule";

/**
 * Public editorial landing page for the private admin surface.
 */
export default function Home() {
  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-ink py-20">
        <Page>
          <div className="space-y-10">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="mono-label m-0">HabitOS · Private operations surface</p>
              <p className="mono-label m-0">Single user · Google sign-in only</p>
            </div>
            <div className="space-y-6">
              <h1 className="display-title m-0 max-w-[11ch]">
                The quiet workshop behind the PDF.
              </h1>
              <p className="section-lede m-0">
                The reMarkable dashboard is the daily surface. This web app is
                where HabitOS gets inspected, recomputed, rendered, and synced.
                Same family, more apparatus visible.
              </p>
            </div>
            <div className="grid gap-4 border-t border-rule pt-6 md:grid-cols-3">
              <div>
                <p className="mono-label m-0">Inspect</p>
                <p className="m-0 text-ink-mid">
                  Source events, month state, render history, and automation
                  status.
                </p>
              </div>
              <div>
                <p className="mono-label m-0">Operate</p>
                <p className="m-0 text-ink-mid">
                  Recompute habits, run renders, start syncs, and kick the
                  nightly flow manually.
                </p>
              </div>
              <div>
                <p className="mono-label m-0">Correct</p>
                <p className="m-0 text-ink-mid">
                  Use the dashboard as a debugging tool, not a second habit
                  tracker.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-4">
              <Link
                className="focus-ring inline-flex h-11 items-center justify-center border border-transparent bg-accent px-6 font-mono text-[11px] tracking-[0.14em] text-paper uppercase no-underline transition-opacity hover:opacity-90"
                href="/login"
              >
                Enter admin
              </Link>
              <Link className="muted-link inline-flex items-center" href="/dashboard">
                Dashboard preview
              </Link>
            </div>
          </div>
        </Page>
      </header>

      <Page>
        <Section
          kicker="Purpose"
          lede="This is not another habit app. It is the operational counterpart to a generated artifact."
          number="01"
          title="Private by default, local-first by design."
        >
          <div className="body-column space-y-4">
            <p className="m-0">
              HabitOS already knows how to ingest WHOOP data, read Day One
              metadata, recompute daily habit entries, render the monthly PDF,
              and prepare safe reMarkable upload instructions. The admin app
              exists to expose those mechanics without turning them into a noisy
              dashboard product.
            </p>
            <p className="m-0">
              Every data request fans out through the Next.js server. The
              browser never reaches the FastAPI backend directly, and the Google
              account allowlist keeps the surface constrained to one operator.
            </p>
          </div>
        </Section>

        <Section
          kicker="Surface map"
          lede="A small set of screens, each with one job."
          number="02"
          title="What lives inside the admin shell."
        >
          <div className="data-column grid gap-6 md:grid-cols-2">
            {[
              ["Dashboard", "Current month pattern, health strip, recent render context."],
              ["Events", "Raw normalized events with month and source filters."],
              ["Habits", "Catalog plus per-habit resolved entries and explanations."],
              ["Automation", "Scheduler posture and on-demand run controls."],
              ["Renders", "Recent render jobs and reMarkable instruction prep."],
              ["Connections", "WHOOP, Day One, reMarkable, and API status surfaces."],
            ].map(([label, description]) => (
              <div className="paper-panel p-5" key={label}>
                <p className="mono-label m-0">{label}</p>
                <Rule />
                <p className="mt-4 mb-0 text-ink-mid">{description}</p>
              </div>
            ))}
          </div>
        </Section>
      </Page>
    </div>
  );
}
