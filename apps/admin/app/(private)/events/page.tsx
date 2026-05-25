import { format } from "date-fns";

import { NoticeBanner } from "@/components/common/notice-banner";
import { PageHeader, Section } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import { formatEventDuration, formatSourceLabel } from "@/lib/formatters";
import { readNotice, resolveSearchParams } from "@/lib/notice";

/**
 * Event explorer for normalized connector payloads.
 */
export default async function EventsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await resolveSearchParams(searchParams);
  const notice = await readNotice(searchParams);
  const month = params.month ?? format(new Date(), "yyyy-MM");
  const source = params.source ?? "";
  const eventType = params.event_type ?? "";
  const start = params.start ?? "";
  const end = params.end ?? "";
  const events = await api.events({
    end: end || undefined,
    event_type: eventType || undefined,
    limit: 200,
    month: month || undefined,
    source: source || undefined,
    start: start || undefined,
  });

  return (
    <div className="space-y-16">
      <PageHeader
        eyebrow="Events"
        subtitle="Normalized source events are the debugging substrate for the rest of the system."
        title="Event explorer"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Filters"
        lede="Month is the default slice. Use explicit date bounds when you need a narrower inspection window."
        number="01"
        title="Query the source events table"
      >
        <form className="data-column grid gap-4 paper-panel p-5 md:grid-cols-2 xl:grid-cols-5" method="GET">
          <label className="space-y-2">
            <span className="field-label">Month</span>
            <Input defaultValue={month} name="month" type="month" />
          </label>
          <label className="space-y-2">
            <span className="field-label">Source</span>
            <select
              className="h-9 w-full appearance-none border-0 border-b border-input bg-transparent py-0.5 font-serif text-sm"
              defaultValue={source}
              name="source"
            >
              <option value="">All sources</option>
              <option value="day_one">Day One</option>
              <option value="manual">Manual</option>
              <option value="whoop">WHOOP</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="field-label">Event type</span>
            <select
              className="h-9 w-full appearance-none border-0 border-b border-input bg-transparent py-0.5 font-serif text-sm"
              defaultValue={eventType}
              name="event_type"
            >
              <option value="">All event types</option>
              <option value="journal">Journal</option>
              <option value="recovery">Recovery</option>
              <option value="sleep">Sleep</option>
              <option value="workout">Workout</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="field-label">Start</span>
            <Input defaultValue={start} name="start" type="date" />
          </label>
          <label className="space-y-2">
            <span className="field-label">End</span>
            <Input defaultValue={end} name="end" type="date" />
          </label>
          <div className="flex items-end">
            <Button className="focus-ring" type="submit" variant="outline">
              Apply filters
            </Button>
          </div>
        </form>
      </Section>

      <Section
        kicker="Results"
        lede="Use this view to confirm ingestion range, event typing, and title normalization."
        number="02"
        title={`${events.length} events`}
      >
        <div className="data-column">
          <Table className="border-y border-rule">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>ID</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Duration</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="font-mono text-[13px] text-ink-mid">
                    {event.id}
                  </TableCell>
                  <TableCell>{formatSourceLabel(event.source)}</TableCell>
                  <TableCell>{event.event_type}</TableCell>
                  <TableCell className="font-mono text-[13px]">
                    {event.local_date}
                  </TableCell>
                  <TableCell className="max-w-[320px] whitespace-normal">
                    <p className="m-0">{event.title || "Untitled event"}</p>
                    <p className="m-0 text-sm text-ink-mid">
                      {event.description || "No description"}
                    </p>
                  </TableCell>
                  <TableCell className="font-mono text-[13px]">
                    {formatEventDuration(event) ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Section>
    </div>
  );
}
