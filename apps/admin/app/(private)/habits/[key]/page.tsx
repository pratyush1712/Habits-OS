import { format } from "date-fns";
import Link from "next/link";

import { NoticeBanner } from "@/components/common/notice-banner";
import { RuleExplanation } from "@/components/habit/rule-explanation";
import { PageHeader, Section } from "@/components/primitives/page";
import { api } from "@/lib/api-client";
import { formatMonthLabel, formatSourceLabel } from "@/lib/formatters";
import { readNotice, resolveSearchParams } from "@/lib/notice";

/**
 * Per-habit view showing the current month’s resolved entries.
 */
export default async function HabitDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ key: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { key } = await params;
  const paramsObject = await resolveSearchParams(searchParams);
  const month = paramsObject.month ?? format(new Date(), "yyyy-MM");
  const notice = await readNotice(searchParams);
  const [habits, entries] = await Promise.all([
    api.habits(),
    api.habitEntries(month),
  ]);
  const habit = habits.find((candidate) => candidate.key === key);
  const habitEntries = entries.filter((entry) => entry.habit_key === key);

  if (!habit) {
    return (
      <div className="space-y-10">
        <PageHeader
          eyebrow="Habits"
          subtitle="The requested habit key was not found in the current catalog."
          title="Missing habit"
        />
        <Link className="muted-link" href="/habits">
          Back to habits
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Habit detail"
        subtitle={`Current month focus · ${formatMonthLabel(month)}`}
        title={habit.label}
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Definition"
        lede="This catalog entry defines whether the habit is automatic or manual, and which event types can satisfy it."
        number="01"
        title="Catalog metadata"
      >
        <div className="data-column grid gap-4 md:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Kind</p>
            <p className="mt-4 mb-0 text-2xl font-light">{habit.kind}</p>
          </section>
          <section className="paper-panel p-5">
            <p className="mono-label m-0">Sources</p>
            <p className="mt-4 mb-0 text-ink-mid">
              {(habit.sources ?? []).map(formatSourceLabel).join(", ") || "—"}
            </p>
          </section>
        </div>
      </Section>

      <Section
        kicker="Resolved entries"
        lede="The current month’s evaluated days are listed newest-first for quick audit work."
        number="02"
        title={`${habitEntries.length} entries in ${formatMonthLabel(month)}`}
      >
        <div className="data-column border-y border-rule">
          {habitEntries
            .sort((left, right) => right.date.localeCompare(left.date))
            .map((entry) => (
              <div className="py-4" key={`${entry.date}:${entry.habit_key}`}>
                <div className="mb-3 flex items-center justify-between">
                  <Link className="muted-link" href={`/day/${entry.date}`}>
                    {entry.date}
                  </Link>
                </div>
                <RuleExplanation entry={entry} />
              </div>
            ))}
        </div>
      </Section>
    </div>
  );
}
