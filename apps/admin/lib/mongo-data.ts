import "server-only";

import {
  MongoClient,
  type AnyBulkWriteOperation,
  type Filter,
  type Sort,
} from "mongodb";

import {
  type EventListResponse,
  type Habit,
  type HabitEntriesResponse,
  type HabitEntry,
  type HabitListResponse,
  type LatestRenderResponse,
  type MedicationDayDose,
  type MedicationGroup,
  type MedicationLogInput,
  type MonthHabitState,
  type RenderJob,
  type RenderJobsResponse,
  type SourceEvent,
} from "./api-client";
import { MEDICATION_PLAN } from "./medication-plan";

const DEFAULT_DB_NAME = "habitos";

type MongoClientGlobal = typeof globalThis & {
  __habitosMongoClientPromise?: Promise<MongoClient>;
};

type MongoConfig = {
  dbName: string;
  uri: string;
};

type MongoDocument = {
  _id?: unknown;
  [key: string]: unknown;
};

type SourceEventDocument = MongoDocument & {
  _id: string;
};

type MedicationMetrics = {
  med_key: string;
  med_label: string;
  prn: boolean;
  scheduled_count: number;
  taken_count: number;
};

function mongoConfig(): MongoConfig | null {
  const uri = process.env.MONGODB_URI;

  if (!uri) {
    return null;
  }

  return {
    dbName: process.env.MONGODB_DB_NAME ?? DEFAULT_DB_NAME,
    uri,
  };
}

export function isMongoDataConfigured(): boolean {
  return mongoConfig() !== null;
}

async function client(): Promise<MongoClient> {
  const config = mongoConfig();

  if (!config) {
    throw new Error("MONGODB_URI is not configured for the admin app.");
  }

  const globalForMongo = globalThis as MongoClientGlobal;

  if (!globalForMongo.__habitosMongoClientPromise) {
    globalForMongo.__habitosMongoClientPromise = new MongoClient(
      config.uri,
    ).connect();
  }

  return globalForMongo.__habitosMongoClientPromise;
}

async function db() {
  const config = mongoConfig();

  if (!config) {
    throw new Error("MONGODB_URI is not configured for the admin app.");
  }

  return (await client()).db(config.dbName);
}

function monthRange(month: string): { end: string; start: string } {
  const [yearPart, monthPart] = month.split("-");
  const year = Number.parseInt(yearPart ?? "", 10);
  const monthNumber = Number.parseInt(monthPart ?? "", 10);

  if (
    !Number.isInteger(year) ||
    !Number.isInteger(monthNumber) ||
    monthNumber < 1 ||
    monthNumber > 12
  ) {
    throw new Error(`Invalid month ${month}; expected YYYY-MM.`);
  }

  const endYear = monthNumber === 12 ? year + 1 : year;
  const endMonth = monthNumber === 12 ? 1 : monthNumber + 1;

  return {
    end: `${endYear.toString().padStart(4, "0")}-${endMonth.toString().padStart(2, "0")}-01`,
    start: `${year.toString().padStart(4, "0")}-${monthNumber.toString().padStart(2, "0")}-01`,
  };
}

function serialize(value: unknown): unknown {
  if (value instanceof Date) {
    return value.toISOString();
  }

  if (Array.isArray(value)) {
    return value.map((item) => serialize(item));
  }

  if (value && typeof value === "object") {
    if ("_bsontype" in value && typeof value.toString === "function") {
      return value.toString();
    }

    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, nested]) => [
        key,
        serialize(nested),
      ]),
    );
  }

  return value;
}

function fromDoc<T>(doc: MongoDocument, options?: { includeId?: boolean }): T {
  const { _id, ...rest } = doc;
  const serialized = serialize(rest) as Record<string, unknown>;

  if (options?.includeId) {
    serialized.id = _id == null ? null : String(_id);
  }

  return serialized as T;
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function nonnegativeInteger(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(0, Math.trunc(value));
  }

  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
  }

  return 0;
}

function medicationGroups(): MedicationGroup[] {
  return MEDICATION_PLAN.map((group) => ({
    key: group.key,
    label: group.label,
    meds: group.meds.map((med) => ({
      dose: med.dose,
      key: med.key,
      label: med.label,
      prn: med.prn ?? false,
      short: med.key === "omega_3" ? "Ω3" : med.label.slice(0, 3),
      total: med.total,
    })),
  }));
}

function medicationDays(events: SourceEvent[]): MedicationDayDose[] {
  const days: MedicationDayDose[] = [];

  for (const event of events) {
    if (event.event_type !== "medication") {
      continue;
    }

    const metrics = record(event.metrics);
    const rawPayload = record(event.raw_payload);
    const medKey = metrics.med_key ?? rawPayload.med_key;

    if (typeof medKey !== "string" || medKey.length === 0) {
      continue;
    }

    const total =
      metrics.scheduled_count ??
      metrics.total_count ??
      metrics.total ??
      rawPayload.scheduled_count ??
      rawPayload.total_count ??
      rawPayload.total;

    days.push({
      date: event.local_date,
      med_key: medKey,
      taken: nonnegativeInteger(
        metrics.taken_count ??
          metrics.taken ??
          rawPayload.taken_count ??
          rawPayload.taken,
      ),
      total: total == null ? null : nonnegativeInteger(total),
    });
  }

  return days.sort((left, right) =>
    `${left.date}:${left.med_key}`.localeCompare(
      `${right.date}:${right.med_key}`,
    ),
  );
}

export async function mongoEvents(query?: {
  end?: string;
  event_type?: string;
  limit?: number;
  month?: string;
  source?: string;
  start?: string;
}): Promise<EventListResponse> {
  const database = await db();
  const filter: Filter<MongoDocument> = {};

  if (query?.month) {
    const range = monthRange(query.month);
    filter.local_date = { $gte: range.start, $lt: range.end };
  } else if (query?.start || query?.end) {
    const localDate: Record<string, string> = {};

    if (query.start) {
      localDate.$gte = query.start;
    }

    if (query.end) {
      localDate.$lte = query.end;
    }

    filter.local_date = localDate;
  }

  if (query?.source) {
    filter.source = query.source;
  }

  if (query?.event_type) {
    filter.event_type = query.event_type;
  }

  const sort: Sort = { local_date: -1, start_time_utc: -1 };
  const docs = await database
    .collection<MongoDocument>("source_events")
    .find(filter)
    .sort(sort)
    .limit(query?.limit ?? 100)
    .toArray();

  return docs.map((doc) => fromDoc<SourceEvent>(doc, { includeId: true }));
}

export async function mongoHabits(): Promise<HabitListResponse> {
  const database = await db();
  const docs = await database
    .collection<MongoDocument>("habits")
    .find({ archived_at: null, enabled: true })
    .sort({ sort_order: 1, _id: 1 })
    .toArray();

  return docs.map((doc) => {
    const habit = fromDoc<Habit & { archived_at?: unknown }>(doc);
    delete habit.archived_at;
    return habit;
  });
}

export async function mongoHabitEntries(
  month: string,
): Promise<HabitEntriesResponse> {
  const database = await db();
  const range = monthRange(month);
  const docs = await database
    .collection<MongoDocument>("habit_entries")
    .find({ date: { $gte: range.start, $lt: range.end } })
    .sort({ date: 1, habit_key: 1 })
    .toArray();

  return docs.map((doc) => fromDoc<HabitEntry>(doc));
}

export async function mongoMonthState(month: string): Promise<MonthHabitState> {
  const [habits, entries, events] = await Promise.all([
    mongoHabits(),
    mongoHabitEntries(month),
    mongoEvents({ limit: 5_000, month }),
  ]);

  return {
    entries,
    generated_at: new Date().toISOString(),
    habits,
    medication_days: medicationDays(events),
    medication_groups: medicationGroups(),
    month,
  };
}

export async function mongoRenderJobs(limit = 12): Promise<RenderJobsResponse> {
  const database = await db();
  const docs = await database
    .collection<MongoDocument>("render_jobs")
    .find()
    .sort({ requested_at: -1 })
    .limit(limit)
    .toArray();

  return docs.map((doc) => fromDoc<RenderJob>(doc, { includeId: true }));
}

export async function mongoLatestRender(
  month?: string,
): Promise<LatestRenderResponse> {
  const database = await db();
  const doc = await database
    .collection<MongoDocument>("render_jobs")
    .findOne(month ? { month } : {}, {
      sort: { requested_at: -1 },
    });

  if (!doc) {
    throw new Error(
      month ? `No render found for ${month}.` : "No render found.",
    );
  }

  return fromDoc<RenderJob>(doc, { includeId: true });
}

export async function mongoLogMedication(
  input: MedicationLogInput,
): Promise<Record<string, unknown>> {
  const database = await db();
  const now = new Date();
  const localDate = input.local_date;
  const observedAt = new Date(`${localDate}T12:00:00.000Z`);
  const timezone = input.timezone ?? "UTC";
  const operations: AnyBulkWriteOperation<SourceEventDocument>[] =
    input.doses.map((dose) => {
      const eventId = `manual:med-${localDate}-${dose.med_key}`;
      const metrics: MedicationMetrics = {
        med_key: dose.med_key,
        med_label: dose.med_label,
        prn: dose.prn ?? false,
        scheduled_count: dose.scheduled_count,
        taken_count: dose.taken_count,
      };

      return {
        replaceOne: {
          filter: { _id: eventId },
          replacement: {
            _id: eventId,
            created_at: now,
            description:
              "Manual medication/supplement dose count from the admin app.",
            end_time_utc: null,
            event_type: "medication",
            local_date: localDate,
            metrics,
            raw_payload: metrics,
            source: "manual",
            source_event_id: `med-${localDate}-${dose.med_key}`,
            start_time_utc: observedAt,
            timezone,
            title: dose.med_label,
            updated_at: now,
          },
          upsert: true,
        },
      };
    });

  if (operations.length === 0) {
    return { events: 0, inserted: 0, local_date: localDate, updated: 0 };
  }

  const result = await database
    .collection<SourceEventDocument>("source_events")
    .bulkWrite(operations, { ordered: false });

  return {
    events: operations.length,
    inserted: result.upsertedCount,
    local_date: localDate,
    month: localDate.slice(0, 7),
    updated: result.modifiedCount,
  };
}
