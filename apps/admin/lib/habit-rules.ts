import "server-only";

import type { EventSource, Habit, HabitEntry, SourceEvent } from "./api-client";

export type HabitStatus = HabitEntry["status"];

export type HabitOverride = {
  date: string;
  description?: string;
  habit_key: string;
  source?: EventSource;
  status: HabitStatus;
  summary?: string;
};

type HabitRuleConfig = {
  journaling: { checkedMinEntries: number };
  medication: { countPrnWithoutSchedule: boolean };
  meditation: { checkedMinMinutes: number; partialMinMinutes: number };
  proteinShake: { checkedMinCount: number };
  recovery: { checkedMinScore: number };
  sleep: { targetHours: number };
  workout: { checkedMinMinutes: number; partialMinMinutes: number };
};

const DEFAULT_RULES: HabitRuleConfig = {
  workout: { checkedMinMinutes: 15, partialMinMinutes: 5 },
  meditation: { checkedMinMinutes: 5, partialMinMinutes: 2 },
  sleep: { targetHours: 7 },
  recovery: { checkedMinScore: 67 },
  journaling: { checkedMinEntries: 1 },
  medication: { countPrnWithoutSchedule: true },
  proteinShake: { checkedMinCount: 1 },
};

type Evaluator = (
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
) => HabitEntry | null;

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

function fmtMin(minutes: number): string {
  return minutes === Math.trunc(minutes) ? `${Math.trunc(minutes)}m` : `${minutes.toFixed(1)}m`;
}

function joinDescriptions(events: SourceEvent[]): string {
  return events
    .map((event) => event.description?.trim() ?? "")
    .filter((description) => description.length > 0)
    .join(" · ");
}

function durationMinutes(event: SourceEvent): number {
  if (!event.end_time_utc) {
    return 0;
  }

  const start = Date.parse(event.start_time_utc);
  const end = Date.parse(event.end_time_utc);

  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return 0;
  }

  return (end - start) / 60_000;
}

function eventMetrics(event: SourceEvent): Record<string, unknown> {
  return record(event.metrics);
}

function daysInMonth(month: string): string[] {
  const [yearPart, monthPart] = month.split("-");
  const year = Number.parseInt(yearPart ?? "", 10);
  const monthNumber = Number.parseInt(monthPart ?? "", 10);
  const lastDay = new Date(year, monthNumber, 0).getDate();

  return Array.from({ length: lastDay }, (_, index) => {
    const day = index + 1;
    return `${year.toString().padStart(4, "0")}-${monthNumber.toString().padStart(2, "0")}-${day.toString().padStart(2, "0")}`;
  });
}

function entryFromOverride(habitKey: string, override: HabitOverride): HabitEntry {
  return {
    confidence: 1,
    date: override.date,
    description: override.description ?? "",
    explanation: "manual override",
    habit_key: habitKey,
    linked_source_event_ids: [],
    manually_overridden: true,
    source: override.source ?? "manual",
    status: override.status,
    summary: override.summary ?? "",
  };
}

function evaluateWorkout(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const workouts = events.filter((event) => event.event_type === "workout");

  if (workouts.length === 0) {
    return null;
  }

  const total = workouts.reduce((sum, event) => sum + durationMinutes(event), 0);
  const rule = config.workout;
  let status: HabitStatus;

  if (total >= rule.checkedMinMinutes) {
    status = "checked";
  } else if (total >= rule.partialMinMinutes) {
    status = "partial";
  } else {
    return null;
  }

  const summary =
    workouts.length === 1
      ? `${fmtMin(durationMinutes(workouts[0]))} ${workouts[0].title || "Workout"}`
      : `${fmtMin(total)} total · ${workouts.length} sessions`;

  return {
    confidence: 1,
    date: day,
    description: joinDescriptions(workouts),
    explanation: `${fmtMin(total)} workout (checked >= ${fmtMin(rule.checkedMinMinutes)}, partial >= ${fmtMin(rule.partialMinMinutes)})`,
    habit_key: "workout",
    linked_source_event_ids: workouts.map((event) => event.id),
    manually_overridden: false,
    source: workouts[0].source,
    status,
    summary,
  };
}

function evaluateMedication(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const medEvents = events.filter((event) => event.event_type === "medication");

  if (medEvents.length === 0) {
    return null;
  }

  let scheduledTotal = 0;
  let takenTotal = 0;
  let prnTaken = 0;
  const details: string[] = [];
  const linkedIds: string[] = [];

  for (const event of medEvents) {
    const metrics = eventMetrics(event);
    const taken = nonnegativeInteger(metrics.taken_count ?? metrics.taken ?? 1);
    const totalValue = metrics.scheduled_count ?? metrics.total_count ?? metrics.total;
    const scheduled =
      totalValue == null ? taken : nonnegativeInteger(totalValue);
    const isPrn = Boolean(metrics.prn);
    const label = String(metrics.med_label ?? event.title ?? metrics.med_key ?? "dose");
    linkedIds.push(event.id);

    if (isPrn && scheduled === 0) {
      if (config.medication.countPrnWithoutSchedule && taken > 0) {
        prnTaken += taken;
        details.push(`${label}: ${taken} PRN`);
      }
      continue;
    }

    scheduledTotal += scheduled;
    takenTotal += scheduled > 0 ? Math.min(taken, scheduled) : taken;

    if (scheduled > 0) {
      details.push(`${label}: ${taken}/${scheduled}`);
    } else if (taken > 0) {
      details.push(`${label}: ${taken}`);
    }
  }

  if (scheduledTotal <= 0) {
    if (prnTaken <= 0) {
      return null;
    }

    return {
      confidence: 1,
      date: day,
      description: details.join(" · "),
      explanation:
        "PRN/as-needed medication was logged; absence of PRN doses is not marked missed.",
      habit_key: "medication",
      linked_source_event_ids: linkedIds,
      manually_overridden: false,
      source: medEvents[0].source,
      status: "checked",
      summary: `${prnTaken} PRN dose${prnTaken === 1 ? "" : "s"}`,
    };
  }

  let status: HabitStatus;
  if (takenTotal >= scheduledTotal) {
    status = "checked";
  } else if (takenTotal > 0) {
    status = "partial";
  } else {
    status = "missed";
  }

  let summary = `${takenTotal}/${scheduledTotal} scheduled doses`;
  if (prnTaken > 0) {
    summary += ` · ${prnTaken} PRN`;
  }

  return {
    confidence: 1,
    date: day,
    description: details.join(" · "),
    explanation: `${takenTotal}/${scheduledTotal} scheduled medication/supplement doses taken. PRN/as-needed doses are informational and are not counted as missed.`,
    habit_key: "medication",
    linked_source_event_ids: linkedIds,
    manually_overridden: false,
    source: medEvents[0].source,
    status,
    summary,
  };
}

function evaluateProteinShake(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const shakes = events.filter((event) => event.event_type === "protein_shake");

  if (shakes.length === 0) {
    return null;
  }

  const total = shakes.reduce(
    (sum, event) => sum + nonnegativeInteger(eventMetrics(event).count ?? 1),
    0,
  );

  if (total < config.proteinShake.checkedMinCount) {
    return null;
  }

  const noun = total === 1 ? "shake" : "shakes";

  return {
    confidence: 1,
    date: day,
    description: joinDescriptions(shakes),
    explanation: `${total} protein ${noun} logged (checked >= ${config.proteinShake.checkedMinCount})`,
    habit_key: "protein_shake",
    linked_source_event_ids: shakes.map((event) => event.id),
    manually_overridden: false,
    source: shakes[0].source,
    status: "checked",
    summary: `${total} ${noun}`,
  };
}

function evaluateMeditation(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const sessions = events.filter((event) => event.event_type === "meditation");

  if (sessions.length === 0) {
    return null;
  }

  const total = sessions.reduce((sum, event) => sum + durationMinutes(event), 0);
  const rule = config.meditation;
  let status: HabitStatus;

  if (total >= rule.checkedMinMinutes) {
    status = "checked";
  } else if (total >= rule.partialMinMinutes) {
    status = "partial";
  } else {
    return null;
  }

  const summary =
    sessions.length === 1
      ? `${fmtMin(durationMinutes(sessions[0]))} ${sessions[0].title || "Session"}`
      : `${fmtMin(total)} total · ${sessions.length} sessions`;

  return {
    confidence: 1,
    date: day,
    description: joinDescriptions(sessions),
    explanation: `${fmtMin(total)} meditation (checked >= ${fmtMin(rule.checkedMinMinutes)}, partial >= ${fmtMin(rule.partialMinMinutes)})`,
    habit_key: "meditation",
    linked_source_event_ids: sessions.map((event) => event.id),
    manually_overridden: false,
    source: sessions[0].source,
    status,
    summary,
  };
}

function sleepSummary(totalMinutes: number, main: SourceEvent): string {
  const hours = Math.floor(totalMinutes / 60);
  const mins = Math.round(totalMinutes - hours * 60);
  const parts = [`${hours}h${mins.toString().padStart(2, "0")}m`];
  const efficiency = eventMetrics(main).efficiency_pct;

  if (efficiency != null) {
    parts.push(`${efficiency}%`);
  }

  return parts.join(" · ");
}

function evaluateSleep(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const sleeps = events.filter((event) => event.event_type === "sleep");

  if (sleeps.length === 0) {
    return null;
  }

  const totalMinutes = sleeps.reduce((sum, event) => sum + durationMinutes(event), 0);
  const targetMinutes = config.sleep.targetHours * 60;
  const status: HabitStatus = totalMinutes >= targetMinutes ? "checked" : "warning";
  const main = sleeps.reduce((best, event) =>
    durationMinutes(event) > durationMinutes(best) ? event : best,
  );

  return {
    confidence: 1,
    date: day,
    description: joinDescriptions(sleeps),
    explanation: `${(totalMinutes / 60).toFixed(1)}h sleep (target ${config.sleep.targetHours}h)`,
    habit_key: "sleep",
    linked_source_event_ids: sleeps.map((event) => event.id),
    manually_overridden: false,
    source: main.source,
    status,
    summary: sleepSummary(totalMinutes, main),
  };
}

function evaluateRecovery(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const recoveries = events.filter((event) => event.event_type === "recovery");
  const scored = recoveries.filter((event) => {
    const metrics = eventMetrics(event);
    return (
      metrics.score_state === "SCORED" &&
      metrics.user_calibrating !== true &&
      metrics.recovery_score != null
    );
  });

  if (scored.length === 0) {
    return null;
  }

  const latest = scored.reduce((best, event) =>
    Date.parse(event.start_time_utc) > Date.parse(best.start_time_utc) ? event : best,
  );
  const score = nonnegativeInteger(eventMetrics(latest).recovery_score);
  const status: HabitStatus =
    score >= config.recovery.checkedMinScore ? "checked" : "warning";

  return {
    confidence: 1,
    date: day,
    description: latest.description ?? "",
    explanation: `Recovery score ${score}% (checked >= ${config.recovery.checkedMinScore}%)`,
    habit_key: "recovery",
    linked_source_event_ids: [latest.id],
    manually_overridden: false,
    source: latest.source,
    status,
    summary: `${score}% recovery`,
  };
}

function evaluateJournaling(
  day: string,
  events: SourceEvent[],
  config: HabitRuleConfig,
): HabitEntry | null {
  const journalEvents = events.filter((event) => event.event_type === "journal");

  if (journalEvents.length === 0) {
    return null;
  }

  const entryCount = journalEvents.reduce(
    (sum, event) => sum + nonnegativeInteger(eventMetrics(event).entry_count ?? 1),
    0,
  );

  if (entryCount < config.journaling.checkedMinEntries) {
    return null;
  }

  const noun = entryCount === 1 ? "entry" : "entries";

  return {
    confidence: 1,
    date: day,
    description: "",
    explanation: `${entryCount} journal entr${entryCount === 1 ? "y" : "ies"} (checked >= ${config.journaling.checkedMinEntries})`,
    habit_key: "journaling",
    linked_source_event_ids: journalEvents.map((event) => event.id),
    manually_overridden: false,
    source: journalEvents[0].source,
    status: "checked",
    summary: `${entryCount} ${noun}`,
  };
}

const EVALUATORS: Record<string, Evaluator> = {
  workout: evaluateWorkout,
  medication: evaluateMedication,
  protein_shake: evaluateProteinShake,
  meditation: evaluateMeditation,
  sleep: evaluateSleep,
  recovery: evaluateRecovery,
  journaling: evaluateJournaling,
};

function evaluateDay(
  day: string,
  habit: Habit,
  events: SourceEvent[],
  override: HabitOverride | undefined,
  config: HabitRuleConfig = DEFAULT_RULES,
): HabitEntry | null {
  if (override) {
    return entryFromOverride(habit.key, override);
  }

  if (habit.kind === "manual") {
    return null;
  }

  const evaluator = EVALUATORS[habit.key];
  return evaluator ? evaluator(day, events, config) : null;
}

/**
 * Mirror of packages/core/rules.py evaluate_month — pure, deterministic month evaluation.
 */
export function evaluateMonth(
  month: string,
  habits: Habit[],
  events: SourceEvent[],
  overrides: HabitOverride[],
  config: HabitRuleConfig = DEFAULT_RULES,
): { entries: HabitEntry[]; month: string } {
  const monthPrefix = `${month}-`;
  const eventsByDate = new Map<string, SourceEvent[]>();

  for (const event of events) {
    if (!event.local_date.startsWith(monthPrefix)) {
      continue;
    }

    const bucket = eventsByDate.get(event.local_date) ?? [];
    bucket.push(event);
    eventsByDate.set(event.local_date, bucket);
  }

  const overridesByKey = new Map<string, HabitOverride>();

  for (const override of overrides) {
    if (!override.date.startsWith(monthPrefix)) {
      continue;
    }

    const key = `${override.date}:${override.habit_key}`;
    overridesByKey.set(key, override);
  }

  const entries: HabitEntry[] = [];

  for (const habit of habits) {
    for (const day of daysInMonth(month)) {
      const override = overridesByKey.get(`${day}:${habit.key}`);
      const dayEvents = eventsByDate.get(day) ?? [];
      const entry = evaluateDay(day, habit, dayEvents, override, config);

      if (entry) {
        entries.push(entry);
      }
    }
  }

  entries.sort((left, right) =>
    `${left.date}:${left.habit_key}`.localeCompare(`${right.date}:${right.habit_key}`),
  );

  return { entries, month };
}
