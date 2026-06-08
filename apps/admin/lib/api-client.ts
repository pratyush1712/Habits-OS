import "server-only";

import type { components, operations } from "./api-types";
import { serverRuntimeConfig } from "./env";

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
type ApiJson<OperationName extends keyof operations> =
  operations[OperationName]["responses"][200]["content"]["application/json"];

export type HealthResponse = ApiJson<"health_health_get">;
export type StatusResponse = ApiJson<"status_status_get">;
export type AutomationStatusResponse = ApiJson<"automation_status_automation_status_get">;
export type EventListResponse = ApiJson<"list_events_events_get">;
export type HabitListResponse = ApiJson<"list_habits_habits_get">;
export type HabitEntriesResponse = ApiJson<"list_habit_entries_habit_entries_get">;
export type MonthStateResponse = ApiJson<"month_state_state_month_get">;
export type RenderJobsResponse = ApiJson<"list_jobs_render_jobs_get">;
export type RenderJobResponse = ApiJson<"render_month_render_month_post">;
export type LatestRenderResponse = ApiJson<"latest_render_latest_get">;
export type RemarkableStatusResponse = ApiJson<"remarkable_status_remarkable_status_get">;
export type RemarkablePathsResponse = ApiJson<"remarkable_paths_remarkable_paths_get">;
export type RemarkableInstructionsResponse = ApiJson<"sync_instructions_remarkable_instructions_get">;
export type WhoopStatusResponse = ApiJson<"whoop_status_whoop_status_get">;
export type DayOneStatusResponse = ApiJson<"dayone_status_dayone_status_get">;
export type SeedDefaultsResponse = ApiJson<"seed_defaults_habits_seed_defaults_post">;
export type SyncResultResponse = components["schemas"]["SyncResult"];
export type Habit = components["schemas"]["Habit"];
export type HabitEntry = components["schemas"]["HabitEntry"];
export type MonthHabitState = components["schemas"]["MonthHabitState"];
export type RenderJob = components["schemas"]["RenderJob"];
export type SourceEvent = components["schemas"]["SourceEvent"];

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
      body: options?.body === undefined ? undefined : JSON.stringify(options.body),
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
    return callApi<EventListResponse>("/events", { query });
  },

  habits(): Promise<HabitListResponse> {
    return callApi<HabitListResponse>("/habits");
  },

  habitEntries(month: string): Promise<HabitEntriesResponse> {
    return callApi<HabitEntriesResponse>("/habit-entries", {
      query: { month },
    });
  },

  monthState(month: string): Promise<MonthStateResponse> {
    return callApi<MonthStateResponse>("/state/month", {
      query: { month },
    });
  },

  renderJobs(limit = 12): Promise<RenderJobsResponse> {
    return callApi<RenderJobsResponse>("/render/jobs", {
      query: { limit },
    });
  },

  latestRender(month?: string): Promise<LatestRenderResponse> {
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

  remarkableInstructions(month: string): Promise<RemarkableInstructionsResponse> {
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
    return callApi<JsonRecord>("/events/medication", {
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
