import "server-only";

import type { components, operations } from "./api-types";
import { serverRuntimeConfig } from "./env";
import {
  isMongoDataConfigured,
  mongoEvents,
  mongoHabitEntries,
  mongoHabits,
  mongoLatestRender,
  mongoLogIntake,
  mongoLogMedication,
  mongoLogProteinShake,
  mongoMonthState,
  mongoRecompute,
  mongoRenderJobs,
} from "./mongo-data";

type JsonRecord = Record<string, unknown>;
type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export type MedicationDoseInput = {
  med_key: string;
  med_label: string;
  prn?: boolean;
  scheduled_count: number;
  taken_count: number;
};

export type MedicationLogInput = {
  doses: MedicationDoseInput[];
  local_date: string;
  timezone?: string;
};

export type ProteinShakeLogInput = {
  count?: number;
  local_date: string;
  timezone?: string;
};

export type IntakeCategory =
  | "adaptogen"
  | "amino_acid"
  | "base"
  | "cacao"
  | "coffee"
  | "collagen"
  | "dairy"
  | "drink"
  | "fat"
  | "fiber"
  | "flavor"
  | "hormone"
  | "mineral"
  | "mushroom"
  | "nootropic"
  | "probiotic"
  | "stimulant"
  | "substance"
  | "supplement"
  | "sweetener"
  | "other";

export type IntakeTimeOfDay =
  | "morning"
  | "afternoon"
  | "evening"
  | "night"
  | "unknown";

export type IntakeItemInput = {
  amount?: number | null;
  brand_key?: string;
  brand_label?: string;
  caffeine_mg?: number | null;
  category?: IntakeCategory;
  ingredient_key?: string;
  ingredient_label?: string;
  product_key?: string;
  product_label?: string;
  key: string;
  label: string;
  notes?: string;
  time_of_day?: IntakeTimeOfDay;
  unit?: string;
};

export type IntakeLogInput = {
  items: IntakeItemInput[];
  local_date: string;
  timezone?: string;
};
type ApiJson<OperationName extends keyof operations> =
  operations[OperationName]["responses"][200]["content"]["application/json"];

export type HealthResponse = ApiJson<"health_health_get">;
export type StatusResponse = ApiJson<"status_status_get">;
export type AutomationStatusResponse =
  ApiJson<"automation_status_automation_status_get">;
export type RenderJobsResponse = ApiJson<"list_jobs_render_jobs_get">;
export type RenderJobResponse = ApiJson<"render_month_render_month_post">;
export type LatestRenderResponse = ApiJson<"latest_render_latest_get">;
export type RemarkableStatusResponse =
  ApiJson<"remarkable_status_remarkable_status_get">;
export type RemarkablePathsResponse =
  ApiJson<"remarkable_paths_remarkable_paths_get">;
export type RemarkableInstructionsResponse =
  ApiJson<"sync_instructions_remarkable_instructions_get">;
export type WhoopStatusResponse = ApiJson<"whoop_status_whoop_status_get">;
export type DayOneStatusResponse = ApiJson<"dayone_status_dayone_status_get">;
export type SeedDefaultsResponse =
  ApiJson<"seed_defaults_habits_seed_defaults_post">;
export type SyncResultResponse = components["schemas"]["SyncResult"];
export type EventSource =
  | "whoop"
  | "muse"
  | "apple_health"
  | "manual"
  | "calendar"
  | "github"
  | "remarkable"
  | "day_one"
  | "medication";
export type EventType =
  | "workout"
  | "sleep"
  | "recovery"
  | "meditation"
  | "deep_work"
  | "journal"
  | "manual"
  | "medication"
  | "protein_shake"
  | "intake";
export type Habit = Omit<
  components["schemas"]["Habit"],
  "event_types" | "sources"
> & {
  event_types?: EventType[];
  sources?: EventSource[];
};
export type HabitEntry = Omit<components["schemas"]["HabitEntry"], "source"> & {
  source: EventSource;
};
export type MedicationItem = {
  dose: string;
  key: string;
  label: string;
  prn?: boolean;
  short: string;
  total: number;
};
export type MedicationGroup = {
  key: string;
  label: string;
  meds: MedicationItem[];
};
export type MedicationDayDose = {
  date: string;
  med_key: string;
  status?: "taken" | "partial" | "missed" | "none" | null;
  taken: number;
  total?: number | null;
};
export type MonthHabitState = {
  entries: HabitEntry[];
  generated_at?: string;
  habits: Habit[];
  medication_days?: MedicationDayDose[];
  medication_groups?: MedicationGroup[];
  month: string;
};
export type MonthStateResponse = MonthHabitState;
export type RenderJob = components["schemas"]["RenderJob"];
export type SourceEvent = Omit<
  components["schemas"]["SourceEvent"],
  "event_type" | "source"
> & {
  event_type: EventType;
  source: EventSource;
};

export type EventListResponse = SourceEvent[];
export type HabitListResponse = Habit[];
export type HabitEntriesResponse = HabitEntry[];

/**
 * Report upstream API failures with enough detail for the admin UI to display.
 */
export class ApiError extends Error {
  readonly statusCode: number;

  constructor(statusCode: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

/**
 * Convert a loose query object into a stable URLSearchParams string.
 */
function toQueryString(query?: QueryParams): string {
  if (!query) {
    return "";
  }

  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }

    params.set(key, `${value}`);
  }

  const serialized = params.toString();

  return serialized.length > 0 ? `?${serialized}` : "";
}

/**
 * Attach the optional admin key only when the backend is configured to expect it.
 */
function buildHeaders(initHeaders?: HeadersInit): HeadersInit {
  const headers = new Headers(initHeaders);

  headers.set("Content-Type", "application/json");

  if (serverRuntimeConfig.apiAdminKeyConfigured) {
    const apiAdminKey = process.env.API_ADMIN_KEY;

    if (apiAdminKey) {
      headers.set("X-HabitOS-Admin-Key", apiAdminKey);
    }
  }

  return headers;
}

/**
 * Shared fetch wrapper for all server-side calls into the FastAPI backend.
 */
async function callApi<ResponseType>(
  path: string,
  options?: {
    cache?: RequestCache;
    body?: unknown;
    method?: "GET" | "POST";
    query?: QueryParams;
  },
): Promise<ResponseType> {
  const queryString = toQueryString(options?.query);
  const response = await fetch(
    `${serverRuntimeConfig.apiBaseUrl}${path}${queryString}`,
    {
      method: options?.method ?? "GET",
      headers: buildHeaders(),
      cache: options?.cache ?? "no-store",
      body:
        options?.body === undefined ? undefined : JSON.stringify(options.body),
    },
  );

  if (!response.ok) {
    const message = await response.text();
    throw new ApiError(
      response.status,
      message || `HabitOS API request failed with ${response.status}.`,
    );
  }

  return (await response.json()) as ResponseType;
}

/**
 * Typed server-only client for the FastAPI control surface.
 */
export const api = {
  health(): Promise<HealthResponse> {
    return callApi<HealthResponse>("/health");
  },

  status(): Promise<StatusResponse> {
    return callApi<StatusResponse>("/status");
  },

  automationStatus(): Promise<AutomationStatusResponse> {
    return callApi<AutomationStatusResponse>("/automation/status");
  },

  events(query?: {
    end?: string;
    event_type?: string;
    limit?: number;
    month?: string;
    source?: string;
    start?: string;
  }): Promise<EventListResponse> {
    if (isMongoDataConfigured()) {
      return mongoEvents(query);
    }

    return callApi<EventListResponse>("/events", { query });
  },

  habits(): Promise<HabitListResponse> {
    if (isMongoDataConfigured()) {
      return mongoHabits();
    }

    return callApi<HabitListResponse>("/habits");
  },

  habitEntries(month: string): Promise<HabitEntriesResponse> {
    if (isMongoDataConfigured()) {
      return mongoHabitEntries(month);
    }

    return callApi<HabitEntriesResponse>("/habit-entries", {
      query: { month },
    });
  },

  monthState(month: string): Promise<MonthStateResponse> {
    if (isMongoDataConfigured()) {
      return mongoMonthState(month);
    }

    return callApi<MonthStateResponse>("/state/month", {
      query: { month },
    });
  },

  renderJobs(limit = 12): Promise<RenderJobsResponse> {
    if (isMongoDataConfigured()) {
      return mongoRenderJobs(limit);
    }

    return callApi<RenderJobsResponse>("/render/jobs", {
      query: { limit },
    });
  },

  latestRender(month?: string): Promise<LatestRenderResponse> {
    if (isMongoDataConfigured()) {
      return mongoLatestRender(month);
    }

    return callApi<LatestRenderResponse>("/render/latest", {
      query: { month },
    });
  },

  remarkableStatus(): Promise<RemarkableStatusResponse> {
    return callApi<RemarkableStatusResponse>("/remarkable/status");
  },

  remarkablePaths(month: string): Promise<RemarkablePathsResponse> {
    return callApi<RemarkablePathsResponse>("/remarkable/paths", {
      query: { month },
    });
  },

  remarkableInstructions(
    month: string,
  ): Promise<RemarkableInstructionsResponse> {
    return callApi<RemarkableInstructionsResponse>("/remarkable/instructions", {
      query: { month },
    });
  },

  whoopStatus(): Promise<WhoopStatusResponse> {
    return callApi<WhoopStatusResponse>("/whoop/status");
  },

  dayOneStatus(): Promise<DayOneStatusResponse> {
    return callApi<DayOneStatusResponse>("/dayone/status");
  },

  async whoopOAuthStart(): Promise<JsonRecord> {
    return callApi<JsonRecord>("/whoop/oauth/start");
  },

  logMedication(input: MedicationLogInput): Promise<JsonRecord> {
    if (isMongoDataConfigured()) {
      return mongoLogMedication(input);
    }

    return callApi<JsonRecord>("/events/medication", {
      body: input,
      method: "POST",
    });
  },

  logProteinShake(input: ProteinShakeLogInput): Promise<JsonRecord> {
    if (isMongoDataConfigured()) {
      return mongoLogProteinShake(input);
    }

    return callApi<JsonRecord>("/events/protein", {
      body: input,
      method: "POST",
    });
  },

  logIntake(input: IntakeLogInput): Promise<JsonRecord> {
    if (isMongoDataConfigured()) {
      return mongoLogIntake(input);
    }

    return callApi<JsonRecord>("/events/intake", {
      body: input,
      method: "POST",
    });
  },

  importSample(): Promise<JsonRecord> {
    return callApi<JsonRecord>("/events/import-sample", { method: "POST" });
  },

  seedDefaults(): Promise<SeedDefaultsResponse> {
    return callApi<SeedDefaultsResponse>("/habits/seed-defaults", {
      method: "POST",
    });
  },

  recompute(month: string): Promise<JsonRecord> {
    if (isMongoDataConfigured()) {
      return mongoRecompute(month);
    }

    return callApi<JsonRecord>("/habits/recompute", {
      method: "POST",
      query: { month },
    });
  },

  renderMonth(month: string): Promise<RenderJobResponse> {
    return callApi<RenderJobResponse>("/render/month", {
      method: "POST",
      query: { month },
    });
  },

  remarkableUpload(
    month: string,
    options?: {
      dry_run?: boolean;
      update?: boolean;
    },
  ): Promise<SyncResultResponse> {
    return callApi<SyncResultResponse>("/remarkable/upload", {
      method: "POST",
      query: {
        month,
        dry_run: options?.dry_run ?? true,
        update: options?.update ?? false,
      },
    });
  },

  nightlyRun(dryRun = true): Promise<JsonRecord> {
    return callApi<JsonRecord>("/automation/nightly-run", {
      method: "POST",
      query: { dry_run: dryRun },
    });
  },

  monthRollover(
    fromMonth: string,
    toMonth: string,
    dryRun = true,
  ): Promise<JsonRecord> {
    return callApi<JsonRecord>("/automation/month-rollover", {
      method: "POST",
      query: {
        dry_run: dryRun,
        from_month: fromMonth,
        to_month: toMonth,
      },
    });
  },

  whoopSync(input: {
    end: string;
    external_user_id: string;
    recompute?: boolean;
    start: string;
  }): Promise<JsonRecord> {
    return callApi<JsonRecord>("/whoop/sync", {
      method: "POST",
      query: input,
    });
  },

  dayOneSync(input: {
    end: string;
    recompute?: boolean;
    start: string;
  }): Promise<JsonRecord> {
    return callApi<JsonRecord>("/dayone/sync", {
      method: "POST",
      query: input,
    });
  },

  pipelineMonth(input: {
    dry_run?: boolean;
    end: string;
    external_user_id: string;
    month: string;
    start: string;
    upload?: boolean;
  }): Promise<JsonRecord> {
    return callApi<JsonRecord>("/pipeline/month", {
      method: "POST",
      query: input,
    });
  },
};
