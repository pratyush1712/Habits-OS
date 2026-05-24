# HabitOS automation

HabitOS now includes a local-first automation layer for nightly sync, month
recompute, PDF rendering, and safe reMarkable document lifecycle preparation.

## What the nightly job does

The nightly pipeline runs this sequence:

1. Resolve local `today` from `HABITOS_TIMEZONE`.
2. Compute the current month.
3. Compute a rolling WHOOP reconciliation window:
   `today - HABITOS_RECONCILE_DAYS` through `today`.
4. Sync WHOOP for that range using `HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID`.
5. Recompute every month touched by the window.
6. Always render the current month PDF.
7. If auto-upload is enabled, prepare/upload the current month to reMarkable.
8. If the day is the first of the month, also render/finalize the previous
   month and prepare its archive target.

The job is local-first: no Celery, Redis, or separate worker infrastructure.

## Environment variables

Add these to `.env`:

```bash
HABITOS_SCHEDULER_ENABLED=false
HABITOS_NIGHTLY_RUN_HOUR=3
HABITOS_NIGHTLY_RUN_MINUTE=0
HABITOS_RECONCILE_DAYS=14
HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID=
HABITOS_AUTO_UPLOAD_REMARKABLE=false
HABITOS_REMARKABLE_DRY_RUN=true
```

Notes:

- `HABITOS_SCHEDULER_ENABLED=false` keeps the scheduler off by default.
- `HABITOS_TIMEZONE` controls both local date resolution and scheduler timezone.
- `HABITOS_REMARKABLE_DRY_RUN=true` is the safest default for manual adapters.

## Manual automation runs

Inspect automation state:

```bash
curl "http://localhost:8000/automation/status"
```

Trigger the nightly pipeline manually:

```bash
curl -X POST "http://localhost:8000/automation/nightly-run?dry_run=true"
```

Force a month rollover manually:

```bash
curl -X POST "http://localhost:8000/automation/month-rollover?from_month=2026-05&to_month=2026-06&dry_run=true"
```

Inspect current/archive reMarkable targets for a month:

```bash
curl "http://localhost:8000/remarkable/paths?month=2026-06"
```

## Monthly rollover

On the first local day of a new month, HabitOS treats rollover specially:

1. Render/finalize the previous month.
2. Prepare/archive the previous month under the archive path.
3. Render the new current month.
4. Keep the new month visible at the fixed current path.

Current month path:

```text
HabitOS/00 Current/00 Current Month - YYYY-MM Habit Dashboard.pdf
```

Archive path:

```text
HabitOS/YYYY/Archive/YYYY-MM Habit Dashboard.pdf
```

## Why archived months are frozen

Archived months are intended to stabilize once they leave the rolling
reconciliation window. That keeps older dashboards calm and predictable on the
device.

There is one deliberate exception: if the previous month is still inside the
WHOOP reconcile window, HabitOS may still recompute and re-render it so late
sleep/recovery updates are not lost. Once that month falls outside the rolling
window, it becomes effectively frozen.

## reMarkable safety rules

- HabitOS only targets machine-owned PDF paths under the `HabitOS` root.
- The manual adapter never mutates the device.
- Manual results return clear instructions with `device_mutated: false`.
- HabitOS does not edit handwritten notebook internals.
- Do not replace unrelated user-owned documents when following manual upload
  instructions.

## Persistent run logging

Each nightly/manual/rollover execution is stored in the `automation_runs`
collection with:

- run type and status
- start and finish timestamps
- reconcile window and affected months
- WHOOP summary
- habit recompute summary
- render summary
- reMarkable summary
- error text when a run fails

This history is append-only and is surfaced by `GET /automation/status`.

## Disabling automation

Set:

```bash
HABITOS_SCHEDULER_ENABLED=false
```

That disables the in-process scheduler entirely. Manual routes remain available.
