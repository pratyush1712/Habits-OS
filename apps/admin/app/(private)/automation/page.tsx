import { format } from "date-fns";

import { JsonPanel } from "@/components/common/json-panel";
import { NoticeBanner } from "@/components/common/notice-banner";
import { PageHeader, Section } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { monthRolloverAction, nightlyRunAction } from "@/lib/actions";
import { api } from "@/lib/api-client";
import { asRecord, readBoolean, readString } from "@/lib/data-helpers";
import { formatDateTimeLabel } from "@/lib/formatters";
import { readNotice } from "@/lib/notice";

const RETURN_PATH = "/automation";

/**
 * Scheduler and automation control surface.
 */
export default async function AutomationPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const notice = await readNotice(searchParams);
  const status = await api.automationStatus();
  const statusRecord = asRecord(status);
  const scheduler = asRecord(statusRecord ? statusRecord.scheduler : null);
  const thisMonth = format(new Date(), "yyyy-MM");

  return (
    <div className="space-y-16">
      <PageHeader
        eyebrow="Automation"
        subtitle="Scheduler posture, reconciliation window, and manual run controls."
        title="Automation control"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Scheduler"
        lede="The admin surface should make background automation legible without pretending it is complex infrastructure."
        number="01"
        title="Current posture"
      >
        <div className="data-column border-y border-rule">
          <div className="grid divide-y divide-rule md:grid-cols-3 md:divide-y-0 md:divide-x md:divide-rule">
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">Enabled</p>
              <p className="m-0 text-[1.6rem] font-light">
                {readBoolean(scheduler, "enabled") ? "Yes" : "No"}
              </p>
            </section>
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">Running</p>
              <p className="m-0 text-[1.6rem] font-light">
                {readBoolean(scheduler, "running") ? "In progress" : "Idle"}
              </p>
            </section>
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">Next run</p>
              <p className="m-0 text-ink-mid">
                {formatDateTimeLabel(readString(scheduler, "next_run_at"))}
              </p>
            </section>
          </div>
        </div>
      </Section>

      <Section
        kicker="Manual runs"
        lede="Dry-run first, then promote to real work only when the output looks sane."
        number="02"
        title="Interventions"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Nightly flow</p>
            <p className="mt-4 mb-4 text-ink-mid">
              Invoke the default WHOOP reconciliation and render pipeline.
            </p>
            <form action={nightlyRunAction}>
              <input name="dryRun" type="hidden" value="true" />
              <input name="returnPath" type="hidden" value={RETURN_PATH} />
              <Button className="focus-ring" type="submit">
                Run nightly flow (dry run)
              </Button>
            </form>
          </section>

          <section className="paper-panel p-5">
            <p className="mono-label m-0">Forced rollover</p>
            <form action={monthRolloverAction} className="mt-4 grid gap-3">
              <input name="dryRun" type="hidden" value="true" />
              <input name="returnPath" type="hidden" value={RETURN_PATH} />
              <label className="space-y-2">
                <span className="field-label">From month</span>
                <Input defaultValue={thisMonth} name="fromMonth" type="month" />
              </label>
              <label className="space-y-2">
                <span className="field-label">To month</span>
                <Input defaultValue={thisMonth} name="toMonth" type="month" />
              </label>
              <Button className="focus-ring" type="submit" variant="outline">
                Prepare rollover
              </Button>
            </form>
          </section>
        </div>
      </Section>

      <Section
        kicker="Payload"
        lede="Until every field earns a handcrafted treatment, the raw response remains visible."
        number="03"
        title="Automation status payload"
      >
        <div className="data-column">
          <JsonPanel data={status} title="automation/status" />
        </div>
      </Section>
    </div>
  );
}
