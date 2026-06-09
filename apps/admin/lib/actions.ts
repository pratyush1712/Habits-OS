"use server";

import { revalidatePath } from "next/cache";
import { redirect, unstable_rethrow } from "next/navigation";

import { api, ApiError, type MedicationDoseInput } from "./api-client";
import { MEDICATION_ITEMS } from "./medication-plan";

/**
 * Read a required string field from an HTML form submission.
 */
function requireField(formData: FormData, name: string): string {
  const value = formData.get(name);

  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Missing required field: ${name}`);
  }

  return value.trim();
}

/**
 * Read an optional boolean flag from an HTML form submission.
 */
function readOptionalNumberField(formData: FormData, name: string): number {
  const value = formData.get(name);

  if (typeof value !== "string" || value.trim().length === 0) {
    return 0;
  }

  const parsed = Number.parseInt(value, 10);

  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`Invalid count for field: ${name}`);
  }

  return parsed;
}

/**
 * Read an optional boolean flag from an HTML form submission.
 */
function readBooleanField(formData: FormData, name: string): boolean {
  const value = formData.get(name);

  return value === "true";
}

/**
 * Attach a lightweight action notice to the return path.
 */
function redirectWithNotice(
  returnPath: string,
  notice: string,
  tone: "error" | "info" = "info",
): never {
  const target = new URL(returnPath, "http://localhost");

  target.searchParams.set("notice", notice);
  target.searchParams.set("tone", tone);

  redirect(`${target.pathname}${target.search}`);
}

/**
 * Convert backend and form failures into compact UI-safe messages.
 */
function toNoticeMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `API ${error.statusCode}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "The request failed.";
}

/**
 * Common path revalidation helper for small admin mutations.
 */
function refreshPaths(paths: string[]): void {
  for (const path of paths) {
    revalidatePath(path);
  }
}

/**
 * Log one day's medication and supplement dose counts from the admin app.
 */
export async function logMedicationAction(formData: FormData): Promise<never> {
  const localDate = requireField(formData, "localDate");
  const timezone = requireField(formData, "timezone");
  const returnPath = requireField(formData, "returnPath");
  const recompute = readBooleanField(formData, "recompute");
  const render = readBooleanField(formData, "render");
  const month = localDate.slice(0, 7);

  const doses: MedicationDoseInput[] = MEDICATION_ITEMS.map((med) => ({
    med_key: med.key,
    med_label: med.label,
    prn: med.prn ?? false,
    scheduled_count: med.total,
    taken_count: readOptionalNumberField(formData, `taken.${med.key}`),
  }));

  try {
    await api.logMedication({
      doses,
      local_date: localDate,
      timezone,
    });

    if (recompute) {
      await api.recompute(month);
    }

    if (render) {
      await api.renderMonth(month);
    }

    refreshPaths([
      "/dashboard",
      "/events",
      "/habits",
      "/medication",
      `/month/${month}`,
      "/renders",
    ]);
    redirectWithNotice(
      returnPath,
      render
        ? `Logged medication data, recomputed, and started render for ${month}.`
        : recompute
          ? `Logged medication data and recomputed ${month}.`
          : "Logged medication data.",
    );
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}


/**
 * Log one day's protein shake count from the admin app.
 */
export async function logProteinShakeAction(formData: FormData): Promise<never> {
  const localDate = requireField(formData, "localDate");
  const timezone = requireField(formData, "timezone");
  const returnPath = requireField(formData, "returnPath");
  const recompute = readBooleanField(formData, "recompute");
  const render = readBooleanField(formData, "render");
  const count = readOptionalNumberField(formData, "count");
  const month = localDate.slice(0, 7);

  try {
    await api.logProteinShake({
      count,
      local_date: localDate,
      timezone,
    });

    if (recompute) {
      await api.recompute(month);
    }

    if (render) {
      await api.renderMonth(month);
    }

    refreshPaths([
      "/dashboard",
      "/events",
      "/habits",
      "/protein-shake",
      `/month/${month}`,
      "/renders",
    ]);
    redirectWithNotice(
      returnPath,
      render
        ? `Logged protein shake, recomputed, and started render for ${month}.`
        : recompute
          ? `Logged protein shake and recomputed ${month}.`
          : "Logged protein shake.",
    );
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}


/**
 * Seed the default habits catalog from the backend.
 */
export async function seedDefaultHabitsAction(formData: FormData): Promise<never> {
  const returnPath = requireField(formData, "returnPath");

  try {
    await api.seedDefaults();
    refreshPaths(["/dashboard", "/habits"]);
    redirectWithNotice(returnPath, "Default habits seeded.");
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Import the bundled sample events to prime a local demo environment.
 */
export async function importSampleEventsAction(formData: FormData): Promise<never> {
  const returnPath = requireField(formData, "returnPath");

  try {
    await api.importSample();
    refreshPaths(["/dashboard", "/events", "/habits"]);
    redirectWithNotice(returnPath, "Sample events imported.");
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Recompute the selected month after source changes or overrides.
 */
export async function recomputeMonthAction(formData: FormData): Promise<never> {
  const month = requireField(formData, "month");
  const returnPath = requireField(formData, "returnPath");

  try {
    await api.recompute(month);
    refreshPaths([
      "/dashboard",
      `/month/${month}`,
      "/events",
      "/habits",
      "/renders",
    ]);
    redirectWithNotice(returnPath, `Recomputed ${month}.`);
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Generate a fresh PDF render for the selected month.
 */
export async function renderMonthAction(formData: FormData): Promise<never> {
  const month = requireField(formData, "month");
  const returnPath = requireField(formData, "returnPath");

  try {
    await api.renderMonth(month);
    refreshPaths(["/dashboard", `/month/${month}`, "/renders"]);
    redirectWithNotice(returnPath, `Started render for ${month}.`);
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Generate the manual reMarkable upload instructions for the selected month.
 */
export async function remarkableUploadAction(formData: FormData): Promise<never> {
  const month = requireField(formData, "month");
  const returnPath = requireField(formData, "returnPath");
  const dryRun = readBooleanField(formData, "dryRun");
  const update = readBooleanField(formData, "update");

  try {
    await api.remarkableUpload(month, {
      dry_run: dryRun,
      update,
    });
    refreshPaths(["/dashboard", "/renders", "/connections"]);
    redirectWithNotice(returnPath, `Prepared reMarkable instructions for ${month}.`);
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Run the backend nightly automation flow on demand.
 */
export async function nightlyRunAction(formData: FormData): Promise<never> {
  const returnPath = requireField(formData, "returnPath");
  const dryRun = readBooleanField(formData, "dryRun");

  try {
    await api.nightlyRun(dryRun);
    refreshPaths(["/dashboard", "/automation", "/renders"]);
    redirectWithNotice(returnPath, "Nightly automation invoked.");
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Force an explicit month rollover for operational recovery work.
 */
export async function monthRolloverAction(formData: FormData): Promise<never> {
  const fromMonth = requireField(formData, "fromMonth");
  const toMonth = requireField(formData, "toMonth");
  const returnPath = requireField(formData, "returnPath");
  const dryRun = readBooleanField(formData, "dryRun");

  try {
    await api.monthRollover(fromMonth, toMonth, dryRun);
    refreshPaths(["/automation", "/renders"]);
    redirectWithNotice(
      returnPath,
      `Month rollover prepared from ${fromMonth} to ${toMonth}.`,
    );
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Trigger a manual Day One sync for the provided date window.
 */
export async function dayOneSyncAction(formData: FormData): Promise<never> {
  const start = requireField(formData, "start");
  const end = requireField(formData, "end");
  const returnPath = requireField(formData, "returnPath");
  const recompute = readBooleanField(formData, "recompute");

  try {
    await api.dayOneSync({ end, recompute, start });
    refreshPaths(["/connections", "/events", "/habits"]);
    redirectWithNotice(returnPath, "Day One sync requested.");
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}

/**
 * Trigger a manual WHOOP sync for the provided user and date window.
 */
export async function whoopSyncAction(formData: FormData): Promise<never> {
  const externalUserId = requireField(formData, "externalUserId");
  const start = requireField(formData, "start");
  const end = requireField(formData, "end");
  const returnPath = requireField(formData, "returnPath");
  const recompute = readBooleanField(formData, "recompute");

  try {
    await api.whoopSync({
      end,
      external_user_id: externalUserId,
      recompute,
      start,
    });
    refreshPaths(["/connections", "/events", "/habits"]);
    redirectWithNotice(returnPath, "WHOOP sync requested.");
  } catch (error) {
    unstable_rethrow(error);
    redirectWithNotice(returnPath, toNoticeMessage(error), "error");
  }
}
