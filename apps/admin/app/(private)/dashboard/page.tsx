import { JsonPanel } from "@/components/common/json-panel";
import { NoticeBanner } from "@/components/common/notice-banner";
import { MonthGrid } from "@/components/habit/month-grid";
import { PageHeader, Section } from "@/components/primitives/page";
import { Numeric } from "@/components/primitives/numeric";
import { Button } from "@/components/ui/button";
import {
  importSampleEventsAction,
  nightlyRunAction,
  recomputeMonthAction,
  renderMonthAction,
  seedDefaultHabitsAction,
} from "@/lib/actions";
import { api } from "@/lib/api-client";
import {
  asRecord,
  readArray,
  readBoolean,
  readString,
} from "@/lib/data-helpers";
import { formatDateTimeLabel, formatRelativeTime } from "@/lib/formatters";
import { readNotice } from "@/lib/notice";

const RETURN_PATH = "/dashboard";

function getCurrentMonthInTimezone(timezone: string): string {
  const formatter = new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    timeZone: timezone,
  });
  const parts = formatter.formatToParts(new Date());
  const year = parts.find((p) => p.type === "year")?.value;
  const month = parts.find((p) => p.type === "month")?.value;
  return `${year}-${month}`;
}

/**
 * Private dashboard home with the current month pattern and common operations.
 */
export default async function DashboardPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const notice = await readNotice(searchParams);
  const statusResult = await api.status().catch(() => null);
  const timezone = readString(asRecord(statusResult), "timezone") || "UTC";
  const currentMonth = getCurrentMonthInTimezone(timezone);
  const [automationResult, monthStateResult, renderJobsResult] =
    await Promise.allSettled([
      api.automationStatus(),
      api.monthState(currentMonth),
      api.renderJobs(6),
    ]);

  const status = statusResult ? asRecord(statusResult) : null;
  const automation =
    automationResult.status === "fulfilled"
      ? asRecord(automationResult.value)
      : null;
  const statusMongo = asRecord(status ? status["mongo"] : null);
  const integrations = asRecord(status ? status["integrations"] : null);
  const whoopIntegration = asRecord(integrations ? integrations["whoop"] : null);
  const latestSync = asRecord(status ? status["latest_sync"] : null);
  const whoopSync = asRecord(latestSync ? latestSync["whoop"] : null);
  const automationScheduler = asRecord(
    automation ? automation["scheduler"] : null,
  );
  const connectedAccountsValue = whoopIntegration?.["connected_accounts"];
  const connectedAccounts =
    typeof connectedAccountsValue === "number"
      ? connectedAccountsValue
      : readArray(whoopIntegration, "accounts").length;

  return (
    <div className="space-y-16">
      <PageHeader
        eyebrow="Dashboard"
        subtitle="The current month at a glance, plus the smallest set of controls needed to keep the pipeline healthy."
        title="Admin dashboard"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Health strip"
        lede="A quiet readout of the system’s current posture."
        number="01"
        title="Current state"
      >
        <div className="data-column border-y border-rule">
          <div className="grid divide-y divide-rule md:grid-cols-2 md:divide-y-0 xl:grid-cols-4 xl:divide-x xl:divide-rule">
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">API</p>
              <h3 className="m-0 text-[1.6rem] font-light">
                {readString(status, "status") ?? "Unavailable"}
              </h3>
              <p className="m-0 text-sm text-ink-mid">
                Mongo connected:{" "}
                {readBoolean(statusMongo, "connected") ? "yes" : "no"}
              </p>
            </section>
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">WHOOP</p>
              <h3 className="m-0 text-[1.6rem] font-light">
                {readBoolean(whoopIntegration, "configured") ? "Configured" : "Pending"}
              </h3>
              <p className="m-0 text-sm text-ink-mid">
                Accounts: <Numeric value={connectedAccounts} />
              </p>
            </section>
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">Automation</p>
              <h3 className="m-0 text-[1.6rem] font-light">
                {readBoolean(automationScheduler, "enabled") ? "Enabled" : "Manual"}
              </h3>
              <p className="m-0 text-sm text-ink-mid">
                Next run:{" "}
                {formatDateTimeLabel(readString(automationScheduler, "next_run_at"))}
              </p>
            </section>
            <section className="space-y-3 px-4 py-5">
              <p className="mono-label m-0">Last WHOOP sync</p>
              <h3 className="m-0 text-[1.6rem] font-light">
                {readString(whoopSync, "status") ?? "Unknown"}
              </h3>
              <p className="m-0 text-sm text-ink-mid">
                {formatRelativeTime(readString(whoopSync, "last_sync_at"))}
              </p>
            </section>
          </div>
        </div>
      </Section>

      <Section
        kicker="Pattern view"
        lede="The month grid remains the fastest way to spot broken ingestion or obviously wrong classifications."
        number="02"
        title={`Current month · ${currentMonth}`}
      >
        {monthStateResult.status === "fulfilled" ? (
          <MonthGrid monthState={monthStateResult.value} />
        ) : (
          <NoticeBanner tone="error">
            {monthStateResult.reason instanceof Error
              ? monthStateResult.reason.message
              : "Failed to load the current month state."}
          </NoticeBanner>
        )}
      </Section>

      <Section
        kicker="Operations"
        lede="Common maintenance actions stay server-side and redirect back here with a persistent notice."
        number="03"
        title="Run small interventions"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Bootstrap</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <form action={seedDefaultHabitsAction}>
                <input name="returnPath" type="hidden" value={RETURN_PATH} />
                <Button className="focus-ring" type="submit" variant="outline">
                  Seed default habits
                </Button>
              </form>
              <form action={importSampleEventsAction}>
                <input name="returnPath" type="hidden" value={RETURN_PATH} />
                <Button className="focus-ring" type="submit" variant="outline">
                  Import sample events
                </Button>
              </form>
            </div>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Current month</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <form action={recomputeMonthAction}>
                <input name="month" type="hidden" value={currentMonth} />
                <input name="returnPath" type="hidden" value={RETURN_PATH} />
                <Button className="focus-ring" type="submit" variant="outline">
                  Recompute {currentMonth}
                </Button>
              </form>
              <form action={renderMonthAction}>
                <input name="month" type="hidden" value={currentMonth} />
                <input name="returnPath" type="hidden" value={RETURN_PATH} />
                <Button className="focus-ring" type="submit">
                  Render {currentMonth}
                </Button>
              </form>
            </div>
          </section>
          <section className="paper-panel p-5 lg:col-span-2">
            <p className="mono-label m-0">Automation</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <form action={nightlyRunAction}>
                <input name="dryRun" type="hidden" value="true" />
                <input name="returnPath" type="hidden" value={RETURN_PATH} />
                <Button className="focus-ring" type="submit">
                  Run nightly flow (dry run)
                </Button>
              </form>
            </div>
          </section>
        </div>
      </Section>

      <Section
        kicker="Telemetry"
        lede="Loose backend payloads stay visible until every endpoint earns a richer typed treatment."
        number="04"
        title="Operational payloads"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <JsonPanel
            data={statusResult || "Failed to load"}
            title="API status"
          />
          <JsonPanel
            data={
              automationResult.status === "fulfilled"
                ? automationResult.value
                : automationResult.reason
            }
            title="Automation status"
          />
          <JsonPanel
            data={
              renderJobsResult.status === "fulfilled"
                ? renderJobsResult.value
                : renderJobsResult.reason
            }
            title="Recent render jobs"
          />
        </div>
      </Section>
    </div>
  );
}
