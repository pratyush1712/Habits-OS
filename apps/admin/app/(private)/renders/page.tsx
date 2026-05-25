import { format } from "date-fns";

import { JsonPanel } from "@/components/common/json-panel";
import { NoticeBanner } from "@/components/common/notice-banner";
import { PageHeader, Section } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { remarkableUploadAction, renderMonthAction } from "@/lib/actions";
import { api } from "@/lib/api-client";
import { readNotice } from "@/lib/notice";

/**
 * Render history and reMarkable preparation surface.
 */
export default async function RendersPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const notice = await readNotice(searchParams);
  const currentMonth = format(new Date(), "yyyy-MM");
  const [jobs, latestRender, remarkableStatus, remarkableInstructions] =
    await Promise.all([
      api.renderJobs(20),
      api.latestRender().catch(() => null),
      api.remarkableStatus(),
      api.remarkableInstructions(currentMonth).catch(() => null),
    ]);
  const returnPath = "/renders";

  return (
    <div className="space-y-16">
      <PageHeader
        eyebrow="Renders"
        subtitle="Rendered PDFs are machine-owned artifacts, and the admin app treats them that way."
        title="Render history"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Current output"
        lede="Keep the current month render one click away from the upload instructions."
        number="01"
        title="Latest artifact"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Latest render</p>
            <p className="mt-4 mb-1 text-2xl font-light">
              {latestRender?.month ?? "No render yet"}
            </p>
            <p className="status-note m-0">
              status · {latestRender?.status ?? "unavailable"}
            </p>
            <p className="mt-2 mb-0 text-ink-mid">
              {latestRender?.output_path ?? "No output path recorded"}
            </p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">reMarkable prep</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <form action={renderMonthAction}>
                <input name="month" type="hidden" value={currentMonth} />
                <input name="returnPath" type="hidden" value={returnPath} />
                <Button className="focus-ring" type="submit">
                  Render {currentMonth}
                </Button>
              </form>
              <form action={remarkableUploadAction}>
                <input name="dryRun" type="hidden" value="true" />
                <input name="month" type="hidden" value={currentMonth} />
                <input name="returnPath" type="hidden" value={returnPath} />
                <input name="update" type="hidden" value="false" />
                <Button className="focus-ring" type="submit" variant="outline">
                  Prepare upload instructions
                </Button>
              </form>
            </div>
          </section>
        </div>
      </Section>

      <Section
        kicker="Render jobs"
        lede="Newest first. Enough detail to confirm cadence and spot failures."
        number="02"
        title={`${jobs.length} recent jobs`}
      >
        <div className="data-column">
          <Table className="border-y border-rule">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>ID</TableHead>
                <TableHead>Month</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Triggered by</TableHead>
                <TableHead>Output path</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id ?? `${job.month}:${job.requested_at}`}>
                  <TableCell className="font-mono text-[13px] text-ink-mid">
                    {job.id ?? "pending"}
                  </TableCell>
                  <TableCell className="font-mono text-[13px]">{job.month}</TableCell>
                  <TableCell className="status-note">{job.status}</TableCell>
                  <TableCell className="status-note">{job.triggered_by}</TableCell>
                  <TableCell className="max-w-[320px] whitespace-normal text-ink-mid">
                    {job.output_path ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Section>

      <Section
        kicker="Payloads"
        lede="The transport shape stays visible while the richer view evolves."
        number="03"
        title="Upload context"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <JsonPanel data={remarkableStatus} title="remarkable/status" />
          <JsonPanel
            data={remarkableInstructions ?? { message: "No instructions available." }}
            title={`remarkable/instructions · ${currentMonth}`}
          />
        </div>
      </Section>
    </div>
  );
}
