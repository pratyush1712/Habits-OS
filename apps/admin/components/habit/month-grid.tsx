import Link from "next/link";
import {
  endOfMonth,
  endOfWeek,
  eachDayOfInterval,
  format,
  isSameMonth,
  parse,
  startOfMonth,
  startOfWeek,
} from "date-fns";

import type { MonthHabitState } from "@/lib/api-client";
import {
  formatMonthLabel,
  mapEntryStatusToGlyph,
  statusToneClass,
} from "@/lib/formatters";

import { StatusGlyph } from "../primitives/status-glyph";

type DayCell = {
  date: Date;
  dateKey: string;
  inMonth: boolean;
};

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/**
 * Build a stable Monday-first calendar grid for the selected month.
 */
function buildCalendarDays(month: string): DayCell[] {
  const monthDate = parse(month, "yyyy-MM", new Date());
  const gridStart = startOfWeek(startOfMonth(monthDate), { weekStartsOn: 1 });
  const gridEnd = endOfWeek(endOfMonth(monthDate), { weekStartsOn: 1 });

  return eachDayOfInterval({ end: gridEnd, start: gridStart }).map((date) => ({
    date,
    dateKey: format(date, "yyyy-MM-dd"),
    inMonth: isSameMonth(date, monthDate),
  }));
}

/**
 * PDF-adjacent month scanner for quickly spotting daily habit patterns.
 */
export function MonthGrid({
  monthState,
  today = format(new Date(), "yyyy-MM-dd"),
}: {
  monthState: MonthHabitState;
  today?: string;
}) {
  const days = buildCalendarDays(monthState.month);
  const entriesByDate = new Map(
    monthState.entries.map((entry) => [
      `${entry.date}:${entry.habit_key}`,
      entry,
    ]),
  );

  return (
    <section className="paper-panel disclose">
      <div className="flex flex-col gap-3 border-b border-rule px-4 py-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <p className="mono-label m-0">Current month pattern</p>
          <h2 className="m-0 text-[clamp(1.75rem,3vw,2.5rem)] font-light tracking-[-0.02em]">
            {formatMonthLabel(monthState.month)}
          </h2>
        </div>
        <Link className="muted-link" href={`/month/${monthState.month}`}>
          Open detailed month view
        </Link>
      </div>
      <div className="overflow-x-auto">
        <div className="grid min-w-[760px] grid-cols-7 border-b border-rule">
          {DAY_LABELS.map((label) => (
            <div
              className="border-r border-rule px-3 py-2 text-[11px] tracking-[0.12em] uppercase text-ink-faint last:border-r-0"
              key={label}
            >
              {label}
            </div>
          ))}
        </div>
        <div className="grid min-w-[760px] grid-cols-7">
          {days.map((day, index) => {
            const entries = monthState.habits.map((habit) =>
              entriesByDate.get(`${day.dateKey}:${habit.key}`) ?? null,
            );
            const isToday = day.dateKey === today;
            const needsRightBorder = (index + 1) % 7 !== 0;
            const notLastRow = index < days.length - 7;

            return (
              <Link
                className={[
                  "group flex min-h-[112px] flex-col gap-3 bg-paper px-3 py-3 no-underline transition-colors hover:bg-paper-deep",
                  day.inMonth ? "text-ink" : "text-ink-ghost",
                  needsRightBorder ? "border-r border-rule" : "",
                  notLastRow ? "border-b border-rule" : "",
                ].join(" ")}
                href={`/day/${day.dateKey}`}
                key={day.dateKey}
              >
                <div className="flex items-center justify-between">
                  <span className="tabular font-mono text-[12px]">
                    {format(day.date, "d")}
                  </span>
                  {isToday ? (
                    <StatusGlyph
                      className="now-pulse text-accent"
                      kind="complete"
                      size={12}
                    />
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-x-1.5 gap-y-1">
                  {entries.map((entry, entryIndex) => {
                    if (!entry) {
                      return (
                        <StatusGlyph
                          className="text-ink-ghost"
                          key={`${day.dateKey}-na-${entryIndex}`}
                          kind="na"
                          size={12}
                        />
                      );
                    }

                    const tone = entry.manually_overridden
                      ? "text-accent"
                      : statusToneClass(entry.status);

                    return (
                      <StatusGlyph
                        className={tone}
                        key={`${entry.date}:${entry.habit_key}`}
                        kind={mapEntryStatusToGlyph(entry.status)}
                        size={12}
                      />
                    );
                  })}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
