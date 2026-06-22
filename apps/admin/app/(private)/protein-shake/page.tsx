import { logProteinShakeAction } from "@/lib/actions";
import { api, type SourceEvent } from "@/lib/api-client";
import { asRecord } from "@/lib/data-helpers";
import { readNotice, resolveSearchParams } from "@/lib/notice";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/primitives/page";
import { NoticeBanner } from "@/components/common/notice-banner";

const RETURN_PATH = "/protein-shake";
const DEFAULT_TIMEZONE = "America/New_York";

function formatDateInTimezone(date: Date, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone: timezone,
    year: "numeric",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return `${values.year}-${values.month}-${values.day}`;
}

function readNumber(record: Record<string, unknown> | null, key: string): number | null {
  if (!record) {
    return null;
  }

  const value = record[key];

  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function proteinCount(events: SourceEvent[]): number {
  for (const event of events) {
    const metrics = asRecord(event.metrics) ?? asRecord(event.raw_payload);
    const count = readNumber(metrics, "count");

    if (count !== null) {
      return count;
    }
  }

  return 1;
}

function fieldClassName(): string {
  return "h-14 w-full border-2 border-slate-950 bg-white px-4 text-2xl font-bold text-slate-950 outline-none focus:border-blue-700 focus:ring-4 focus:ring-yellow-300";
}

function buttonClassName(color: "blue" | "green" | "white" = "blue"): string {
  if (color === "green") {
    return "inline-flex min-h-14 items-center justify-center border-2 border-slate-950 bg-green-500 px-6 py-3 text-center text-lg font-black uppercase tracking-wide text-slate-950 no-underline hover:bg-green-400 active:translate-y-0.5";
  }

  if (color === "white") {
    return "inline-flex min-h-14 items-center justify-center border-2 border-slate-950 bg-white px-6 py-3 text-center text-lg font-black uppercase tracking-wide text-slate-950 no-underline hover:bg-yellow-200 active:translate-y-0.5";
  }

  return "inline-flex min-h-14 items-center justify-center border-2 border-slate-950 bg-blue-600 px-6 py-3 text-center text-lg font-black uppercase tracking-wide text-white no-underline hover:bg-blue-500 active:translate-y-0.5";
}

export default async function ProteinShakePage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await resolveSearchParams(searchParams);
  const notice = await readNotice(searchParams);
  const selectedDate = params.date ?? formatDateInTimezone(new Date(), DEFAULT_TIMEZONE);
  const month = selectedDate.slice(0, 7);
  const events = await api.events({
    end: selectedDate,
    event_type: "protein_shake",
    limit: 10,
    start: selectedDate,
  });
  const count = proteinCount(events);

  return (
    <div className="mx-auto space-y-6">
      <PageHeader
        actions={
          <form action={logProteinShakeAction}>
            <input name="localDate" type="hidden" value={selectedDate} />
            <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
            <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />
            <input name="count" type="hidden" value={count} />
            <Button className="focus-ring" type="submit">
              Save protein
            </Button>
          </form>
        }
        eyebrow="Protein"
        subtitle="Log how many protein servings you had today."
        title="Protein tracker"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <section className="mt-6 border-4 border-slate-950 bg-blue-100 p-5">
        <h2 className="m-0 text-2xl font-black">Pick date</h2>
        <form className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end" method="GET">
          <label className="block flex-1">
            <span className="mb-2 block text-lg font-black">Date</span>
            <input className={fieldClassName()} defaultValue={selectedDate} name="date" type="date" />
          </label>
          <button className={buttonClassName("blue")} type="submit">
            Load
          </button>
        </form>
      </section>

      <form action={logProteinShakeAction} className="mt-6">
        <input name="localDate" type="hidden" value={selectedDate} />
        <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
        <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />

        <section className="border-4 border-slate-950 bg-white p-5">
          <h2 className="m-0 border-b-4 border-slate-950 pb-3 text-3xl font-black uppercase">
            Protein servings
          </h2>
          <label className="mt-5 block border-2 border-slate-950 bg-slate-50 p-4">
            <span className="block text-2xl font-black">How many today?</span>
            <span className="block text-base font-bold text-slate-700">
              Logged as a single daily count. Zero leaves the day blank (not missed).
            </span>
            <input
              className={`${fieldClassName()} mt-3`}
              defaultValue={count}
              inputMode="numeric"
              max={20}
              min={0}
              name="count"
              type="number"
            />
          </label>
        </section>

        <section className="mt-6 border-4 border-slate-950 bg-white p-5">
          <h2 className="m-0 text-2xl font-black">After saving</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="flex gap-3 border-2 border-slate-950 bg-green-100 p-4 text-xl font-black">
              <input className="mt-1 size-6" defaultChecked name="recompute" type="checkbox" value="true" />
              <span>Recompute {month}</span>
            </label>
            <label className="flex gap-3 border-2 border-slate-950 bg-blue-100 p-4 text-xl font-black">
              <input className="mt-1 size-6" name="render" type="checkbox" value="true" />
              <span>Render PDF too</span>
            </label>
          </div>
          <button className={`${buttonClassName("blue")} mt-5 w-full sm:w-auto`} type="submit">
            Save protein
          </button>
        </section>
      </form>

      <section className="mt-6 border-4 border-slate-950 bg-white p-5">
        <h2 className="m-0 text-2xl font-black">Already saved for {selectedDate}</h2>
        {events.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[480px] border-collapse text-left">
              <thead>
                <tr className="bg-slate-950 text-white">
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Log</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Count</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">ID</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => {
                  const metrics = asRecord(event.metrics) ?? asRecord(event.raw_payload);
                  const loggedCount = readNumber(metrics, "count") ?? 0;

                  return (
                    <tr key={event.id}>
                      <td className="border-2 border-slate-950 p-3 text-lg font-bold">
                        {event.title || "Protein"}
                      </td>
                      <td className="border-2 border-slate-950 p-3 font-mono text-lg font-black">
                        {loggedCount}
                      </td>
                      <td className="border-2 border-slate-950 p-3 font-mono text-sm font-bold">
                        {event.id}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 border-2 border-slate-950 bg-yellow-200 p-4 text-xl font-black">
            Nothing saved for this date yet.
          </p>
        )}
      </section>
    </div>
  );
}
