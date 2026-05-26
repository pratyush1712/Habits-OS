# HabitOS automation

HabitOS now includes a local-first automation layer for nightly sync, month
recompute, PDF rendering, and safe reMarkable document lifecycle preparation.

> **Adding a new integration to this pipeline?** Read
> [docs/integration_blueprint.md](integration_blueprint.md) first. Every
> integration that participates in nightly automation must conform to the
> Automation Compatibility Contract in that document and return an
> `IntegrationSyncSummary` (see
> [`packages/connectors/base.py`](../packages/connectors/base.py)) from its
> `sync_range` method.

## What the nightly job does

The nightly pipeline runs this sequence:

1. Resolve local `today` from `HABITOS_TIMEZONE`.
2. Compute the current month.
3. Compute a rolling WHOOP reconciliation window:
   `today - HABITOS_RECONCILE_DAYS` through `today`.
4. Sync WHOOP for that range using `HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID`.
5. If `DAYONE_DB_PATH` is set, sync Day One for the same range (metadata-only
   by default). Missing path / unreadable DB / unsupported schema all return
   a skipped `IntegrationSyncSummary`; nightly automation does not fail.
6. Recompute every month touched by the union of WHOOP and Day One affected
   months.
7. Always render the current month PDF.
8. If auto-upload is enabled, prepare/upload the current month to reMarkable.
9. If the day is the first of the month, also render/finalize the previous
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

# Day One (optional; leave DAYONE_DB_PATH empty to disable)
DAYONE_SYNC_MODE=sqlite
DAYONE_DB_PATH=
DAYONE_INCLUDE_TEXT=false
DAYONE_LOOKBACK_DAYS=3
DAYONE_JOURNAL_FILTER=
DAYONE_TIMEZONE=UTC
```

Notes:

- `HABITOS_SCHEDULER_ENABLED=false` keeps the scheduler off by default.
- `HABITOS_TIMEZONE` controls both local date resolution and scheduler timezone.
- `HABITOS_REMARKABLE_DRY_RUN=true` is the safest default for manual adapters.
- `DAYONE_DB_PATH` empty ⇒ Day One sync is skipped cleanly each night and
  `dayone_summary.skipped_reason` is recorded as `"missing_db_path"`. The
  rest of the pipeline runs unchanged.
- `DAYONE_INCLUDE_TEXT=false` is the default and the recommended value. Even
  with `true`, raw entry text is never persisted in `source_events.raw_payload`;
  only a derived word count joins `metrics.total_word_count`.

## Manual automation runs

Inspect automation state:

```bash
curl "http://localhost:8083/automation/status"
```

Trigger the nightly pipeline manually:

```bash
curl -X POST "http://localhost:8083/automation/nightly-run?dry_run=true"
```

Force a month rollover manually:

```bash
curl -X POST "http://localhost:8083/automation/month-rollover?from_month=2026-05&to_month=2026-06&dry_run=true"
```

Inspect current/archive reMarkable targets for a month:

```bash
curl "http://localhost:8083/remarkable/paths?month=2026-06"
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

## reMarkable adapter selection

Nightly automation uses whichever adapter is selected by
`HABITOS_REMARKABLE_ADAPTER`. With `manual` (default) the nightly job
produces upload instructions and `device_mutated=false`. With `rmapi`
and `HABITOS_AUTO_UPLOAD_REMARKABLE=true` and
`HABITOS_REMARKABLE_DRY_RUN=false`, the nightly job actually pushes the
current-month dashboard to the reMarkable Cloud via the
[ddvk/rmapi](https://github.com/ddvk/rmapi) CLI.

See [remarkable_sync.md](remarkable_sync.md#automated-adapter-rmapi)
for setup and safety details.

### Upload failures don't erase renders

Each upload call in `AutomationService` is wrapped so that any adapter
exception is recorded as a failed sync result in
`automation_runs.remarkable_summary` without aborting the run. The
preceding render result is already persisted by the time upload runs,
so a transient rmapi or network problem can never destroy a successful
render. Resolve the rmapi issue and re-trigger the upload manually via
`POST /remarkable/upload?month=YYYY-MM` when convenient.

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
- Day One summary (counts, inserted/updated, affected months,
  `skipped_reason`, warnings — journal names, tags, and entry UUIDs are
  intentionally not exposed here)
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
