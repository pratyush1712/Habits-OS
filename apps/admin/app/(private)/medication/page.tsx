import { logMedicationAction } from "@/lib/actions";
import { api, type SourceEvent } from "@/lib/api-client";
import { asRecord, readString } from "@/lib/data-helpers";
import { MEDICATION_PLAN } from "@/lib/medication-plan";
import { readNotice, resolveSearchParams } from "@/lib/notice";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/primitives/page";
import { NoticeBanner } from "@/components/common/notice-banner";

const RETURN_PATH = "/medication";
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

function doseDefaults(events: SourceEvent[]): Record<string, number> {
  const counts: Record<string, number> = {};

  for (const event of events) {
    const metrics = asRecord(event.metrics) ?? asRecord(event.raw_payload);
    const medKey = readString(metrics, "med_key");
    const takenCount = readNumber(metrics, "taken_count");

    if (medKey && takenCount !== null) {
      counts[medKey] = takenCount;
    }
  }

  return counts;
}

function doseSummary(event: SourceEvent): string {
  const metrics = asRecord(event.metrics) ?? asRecord(event.raw_payload);
  const taken = readNumber(metrics, "taken_count") ?? 0;
  const scheduled = readNumber(metrics, "scheduled_count") ?? 0;
  const medKey = readString(metrics, "med_key") ?? event.title;

  return scheduled > 0 ? `${medKey}: ${taken}/${scheduled}` : `${medKey}: ${taken} PRN`;
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

export default async function MedicationPage({
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
    event_type: "medication",
    limit: 80,
    start: selectedDate,
  });
  const counts = doseDefaults(events);

  return (
    <div className="mx-auto space-y-6">
      <PageHeader
        actions={
          <form action={logMedicationAction}>
            <input name="localDate" type="hidden" value={selectedDate} />
            <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
            <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />
            <Button className="focus-ring" type="submit">
              Save medication log
            </Button>
          </form>
        }
        eyebrow="Medication"
        subtitle="Log your medication and supplements for today."
        title="Medication tracker"
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

      <form action={logMedicationAction} className="mt-6">
        <input name="localDate" type="hidden" value={selectedDate} />
        <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
        <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />

        <div className="grid gap-5 lg:grid-cols-3">
          {MEDICATION_PLAN.map((group) => (
            <section className="border-4 border-slate-950 bg-white p-5" key={group.key}>
              <h2 className="m-0 border-b-4 border-slate-950 pb-3 text-3xl font-black uppercase">
                {group.label}
              </h2>
              <div className="mt-5 space-y-5">
                {group.meds.map((med) => (
                  <label className="block border-2 border-slate-950 bg-slate-50 p-4" key={med.key}>
                    <span className="flex items-start justify-between gap-4">
                      <span>
                        <span className="block text-2xl font-black">{med.label}</span>
                        <span className="block text-base font-bold text-slate-700">{med.dose}</span>
                      </span>
                      <span className="bg-yellow-300 px-2 py-1 text-lg font-black">
                        {med.prn ? "PRN" : `/${med.total}`}
                      </span>
                    </span>
                    <input
                      className={`${fieldClassName()} mt-3`}
                      defaultValue={counts[med.key] ?? 0}
                      inputMode="numeric"
                      min={0}
                      name={`taken.${med.key}`}
                      type="number"
                    />
                    {med.notes ? (
                      <span className="mt-2 block text-base font-bold text-slate-700">
                        {med.notes}
                      </span>
                    ) : null}
                  </label>
                ))}
              </div>
            </section>
          ))}
        </div>

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
            Save medication log
          </button>
        </section>
      </form>

      <section className="mt-6 border-4 border-slate-950 bg-white p-5">
        <h2 className="m-0 text-2xl font-black">Already saved for {selectedDate}</h2>
        {events.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[680px] border-collapse text-left">
              <thead>
                <tr className="bg-slate-950 text-white">
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Medication</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Count</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">ID</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td className="border-2 border-slate-950 p-3 text-lg font-bold">
                      {event.title || "Medication"}
                    </td>
                    <td className="border-2 border-slate-950 p-3 font-mono text-lg font-black">
                      {doseSummary(event)}
                    </td>
                    <td className="border-2 border-slate-950 p-3 font-mono text-sm font-bold">
                      {event.id}
                    </td>
                  </tr>
                ))}
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
