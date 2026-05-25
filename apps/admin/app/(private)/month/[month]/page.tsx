import Link from "next/link";

import { NoticeBanner } from "@/components/common/notice-banner";
import { MonthGrid } from "@/components/habit/month-grid";
import { PageHeader, Section } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";
import {
  recomputeMonthAction,
  remarkableUploadAction,
  renderMonthAction,
} from "@/lib/actions";
import { api } from "@/lib/api-client";
import { asRecord, readString } from "@/lib/data-helpers";
import { formatDateLabel, formatMonthLabel } from "@/lib/formatters";
import { readNotice } from "@/lib/notice";

/**
 * Full-month detail view centered on the rendered month state.
 */
export default async function MonthPage({
  params,
  searchParams,
}: {
  params: Promise<{ month: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { month } = await params;
  const notice = await readNotice(searchParams);
  const [monthState, latestRender, remarkablePaths] = await Promise.all([
    api.monthState(month),
    api.latestRender(month).catch(() => null),
    api.remarkablePaths(month).catch(() => null),
  ]);
  const remarkableCurrent = asRecord(remarkablePaths ? remarkablePaths["current"] : null);
  const remarkableArchive = asRecord(remarkablePaths ? remarkablePaths["archive"] : null);
  const groupedDates = Array.from(
    new Set(monthState.entries.map((entry) => entry.date)),
  ).sort((left, right) => right.localeCompare(left));
  const returnPath = `/month/${month}`;

  return (
    <div className="space-y-16">
      <PageHeader
        actions={
          <>
            <form action={recomputeMonthAction}>
              <input name="month" type="hidden" value={month} />
              <input name="returnPath" type="hidden" value={returnPath} />
              <Button className="focus-ring" type="submit" variant="outline">
                Recompute
              </Button>
            </form>
            <form action={renderMonthAction}>
              <input name="month" type="hidden" value={month} />
              <input name="returnPath" type="hidden" value={returnPath} />
              <Button className="focus-ring" type="submit">
                Render PDF
              </Button>
            </form>
          </>
        }
        eyebrow="Month view"
        subtitle="A fuller look at one month’s resolved state, render context, and upload targets."
        title={formatMonthLabel(month)}
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Calendar"
        lede="The scanner view stays first, because pattern recognition beats line-by-line inspection for gross errors."
        number="01"
        title="Resolved month state"
      >
        <MonthGrid monthState={monthState} />
      </Section>

      <Section
        kicker="Render context"
        lede="Rendered artifacts and reMarkable targets stay attached to the same month, not hidden in a separate tool."
        number="02"
        title="Render and upload targets"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Latest render</p>
            <p className="mt-4 mb-0 text-2xl font-light">
              {latestRender?.status ?? "No render yet"}
            </p>
            <p className="mt-2 mb-0 text-ink-mid">
              Output path: {latestRender?.output_path ?? "Not available"}
            </p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">reMarkable targets</p>
            <div className="mt-4 space-y-3 text-ink-mid">
              <p className="m-0">
                Current: {readString(remarkableCurrent, "path") ?? "Unavailable"}
              </p>
              <p className="m-0">
                Archive: {readString(remarkableArchive, "path") ?? "Unavailable"}
              </p>
              <form action={remarkableUploadAction}>
                <input name="dryRun" type="hidden" value="true" />
                <input name="month" type="hidden" value={month} />
                <input name="returnPath" type="hidden" value={returnPath} />
                <input name="update" type="hidden" value="false" />
                <Button className="focus-ring mt-2" type="submit" variant="outline">
                  Prepare manual upload instructions
                </Button>
              </form>
            </div>
          </section>
        </div>
      </Section>

      <Section
        kicker="Day index"
        lede="When something looks wrong in the grid, jump straight into the affected day."
        number="03"
        title="Days in this month"
      >
        <div className="data-column divide-y divide-rule border-y border-rule">
          {groupedDates.map((date) => {
            const dayEntries = monthState.entries.filter((entry) => entry.date === date);

            return (
              <div className="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between" key={date}>
                <div className="space-y-1">
                  <p className="m-0">{formatDateLabel(date)}</p>
                  <p className="mono-label m-0">{dayEntries.length} habit entries</p>
                </div>
                <Link className="muted-link" href={`/day/${date}`}>
                  Open day detail
                </Link>
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}
