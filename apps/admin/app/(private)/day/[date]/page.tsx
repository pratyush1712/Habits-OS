import Link from "next/link";

import { NoticeBanner } from "@/components/common/notice-banner";
import { RuleExplanation } from "@/components/habit/rule-explanation";
import { PageHeader, Section } from "@/components/primitives/page";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import {
  formatDateLabel,
  formatEventDuration,
  formatSourceLabel,
  formatStatusLabel,
} from "@/lib/formatters";
import { readNotice } from "@/lib/notice";

/**
 * Daily inspection view combining resolved habit entries with raw source events.
 */
export default async function DayPage({
  params,
  searchParams,
}: {
  params: Promise<{ date: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { date } = await params;
  const notice = await readNotice(searchParams);
  const month = date.slice(0, 7);
  const [monthState, events] = await Promise.all([
    api.monthState(month),
    api.events({ limit: 300, month }),
  ]);
  const dayEntries = monthState.entries.filter((entry) => entry.date === date);
  const dayEvents = events.filter((event) => event.local_date === date);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Day detail"
        subtitle="Resolved habit explanations stay beside the raw source events that produced them."
        title={formatDateLabel(date)}
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Resolved habits"
        lede="The rule engine output comes first, because this is the surface you are auditing."
        number="01"
        title="Habit entries"
      >
        <div className="data-column border-y border-rule">
          {dayEntries.length > 0 ? (
            dayEntries.map((entry) => (
              <RuleExplanation entry={entry} key={`${entry.date}:${entry.habit_key}`} />
            ))
          ) : (
            <div className="py-6 text-ink-mid">No habit entries were resolved for this day.</div>
          )}
        </div>
      </Section>

      <Section
        kicker="Source events"
        lede="These are the normalized facts the rule engine received for the same date."
        number="02"
        title="Raw event trace"
      >
        <div className="data-column space-y-4">
          {dayEvents.length > 0 ? (
            <Table className="table-fixed border-y border-rule">
              <colgroup>
                <col className="w-[10%]" />
                <col className="w-[12%]" />
                <col className="w-[38%]" />
                <col className="w-[30%]" />
                <col className="w-[10%]" />
              </colgroup>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Source</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Start</TableHead>
                  <TableHead>Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dayEvents.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="font-mono text-[13px] whitespace-nowrap">
                      {formatSourceLabel(event.source)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{event.event_type}</TableCell>
                    <TableCell className="whitespace-normal">
                      <p className="m-0">{event.title || "Untitled event"}</p>
                      <p className="m-0 text-sm text-ink-mid">
                        {event.description || "No description"}
                      </p>
                    </TableCell>
                    <TableCell className="break-all font-mono text-[13px] whitespace-normal">
                      {event.start_time_utc}
                    </TableCell>
                    <TableCell className="font-mono text-[13px]">
                      {formatEventDuration(event) ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="paper-panel p-5 text-ink-mid">
              No source events matched this date.
            </div>
          )}

          <div className="flex flex-wrap gap-4 text-sm text-ink-mid">
            <Link className="muted-link" href={`/month/${month}`}>
              Back to {month}
            </Link>
            {dayEntries[0] ? (
              <span>{formatStatusLabel(dayEntries[0].status)} is shown first by design.</span>
            ) : null}
          </div>
        </div>
      </Section>
    </div>
  );
}
