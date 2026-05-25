import Link from "next/link";
import { format } from "date-fns";

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
import { seedDefaultHabitsAction } from "@/lib/actions";
import { api } from "@/lib/api-client";
import { formatSourceLabel } from "@/lib/formatters";
import { readNotice } from "@/lib/notice";

const RETURN_PATH = "/habits";

/**
 * Habit catalog and current-month coverage view.
 */
export default async function HabitsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const currentMonth = format(new Date(), "yyyy-MM");
  const notice = await readNotice(searchParams);
  const [habits, entries] = await Promise.all([
    api.habits(),
    api.habitEntries(currentMonth),
  ]);

  return (
    <div className="space-y-16">
      <PageHeader
        actions={
          <form action={seedDefaultHabitsAction}>
            <input name="returnPath" type="hidden" value={RETURN_PATH} />
            <Button className="focus-ring" type="submit" variant="outline">
              Seed defaults
            </Button>
          </form>
        }
        eyebrow="Habits"
        subtitle="The catalog defines what the renderer tries to resolve and what stays manual-only."
        title="Habit catalog"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Catalog"
        lede="A small table is enough here. The point is clarity, not dashboard theater."
        number="01"
        title={`${habits.length} habits`}
      >
        <div className="data-column">
          <Table className="border-y border-rule">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Habit</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Sources</TableHead>
                <TableHead>{currentMonth}</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {habits.map((habit) => {
                const habitEntries = entries.filter(
                  (entry) => entry.habit_key === habit.key,
                );
                const checkedCount = habitEntries.filter(
                  (entry) => entry.status === "checked" || entry.status === "manual",
                ).length;

                return (
                  <TableRow key={habit.key}>
                    <TableCell className="max-w-[260px] whitespace-normal">
                      <p className="m-0">{habit.label}</p>
                      <p className="m-0 text-sm text-ink-mid">
                        {habit.description || "No description"}
                      </p>
                    </TableCell>
                    <TableCell>{habit.kind}</TableCell>
                    <TableCell className="max-w-[220px] whitespace-normal text-ink-mid">
                      {(habit.sources ?? []).map(formatSourceLabel).join(", ") || "—"}
                    </TableCell>
                    <TableCell className="font-mono text-[13px]">
                      {checkedCount} / {habitEntries.length}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link className="muted-link" href={`/habits/${habit.key}`}>
                        Open
                      </Link>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </Section>
    </div>
  );
}
