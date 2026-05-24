# HabitOS Local API

HabitOS exposes a small local-first FastAPI control surface for manually running the pipeline:
WHOOP sync → habit recompute → derived month state → PDF render → optional reMarkable upload instructions.

Run locally:

```bash
make run-api
# or
uvicorn apps.api.main:app --reload --host localhost --port 8000
```

Base URL: `http://localhost:8000`

## Happy-path workflow

Set your values once:

```bash
BASE="http://localhost:8000"
MONTH="2026-05"
START="2026-05-01"
END="2026-05-31"
WHOOP_USER_ID="your-whoop-user-id"
```

Check health and status:

```bash
curl "$BASE/health"
curl "$BASE/status"
```

Connect WHOOP if needed:

```bash
curl "$BASE/whoop/oauth/start"
# Open authorization_url in a browser, authorize, then let WHOOP redirect to /whoop/oauth/callback?code=...&state=...
curl "$BASE/whoop/status"
```

Run each step manually:

```bash
curl -X POST "$BASE/whoop/sync?external_user_id=$WHOOP_USER_ID&start=$START&end=$END"
curl -X POST "$BASE/habits/recompute?month=$MONTH"
curl "$BASE/habit-entries?month=$MONTH"
curl "$BASE/state/month?month=$MONTH"
curl -X POST "$BASE/render/month?month=$MONTH"
curl "$BASE/render/latest"
curl -X POST "$BASE/remarkable/upload?month=$MONTH&dry_run=true"
```

Run the whole month pipeline:

```bash
curl -X POST "$BASE/pipeline/month?external_user_id=$WHOOP_USER_ID&start=$START&end=$END&month=$MONTH&upload=false"
curl -X POST "$BASE/pipeline/month?external_user_id=$WHOOP_USER_ID&start=$START&end=$END&month=$MONTH&upload=true&dry_run=true"
curl -X POST "$BASE/pipeline/month?external_user_id=$WHOOP_USER_ID&start=$START&end=$END&month=$MONTH&upload=true&dry_run=false"
```

`dry_run=false` with the current manual reMarkable adapter still does not mutate the device; it returns ready-to-upload instructions.

Run nightly automation manually:

```bash
curl "$BASE/automation/status"
curl -X POST "$BASE/automation/nightly-run?dry_run=true"
curl -X POST "$BASE/automation/month-rollover?from_month=2026-05&to_month=2026-06&dry_run=true"
curl "$BASE/remarkable/paths?month=$MONTH"
```

## Routes

### GET /health

Liveness plus Mongo ping.

Request:

```bash
curl "$BASE/health"
```

Response:

```json
{
  "status": "ok",
  "mongo": "connected"
}
```

If Mongo is unavailable, returns `503` with a diagnostic detail.

### GET /status

Summarizes Mongo connection, configured integrations, latest render job, and latest sync status.

Request:

```bash
curl "$BASE/status"
```

Response:

```json
{
  "status": "ok",
  "mongo": { "connected": true, "database": "habitos" },
  "integrations": {
    "whoop": {
      "configured": true,
      "connected_accounts": 1,
      "scopes": ["offline", "read:workout"]
    },
    "remarkable": {
      "configured": true,
      "adapter": "manual",
      "mode": "manual_upload",
      "machine_owned_root": "HabitOS"
    }
  },
  "latest_render_job": null,
  "latest_sync": {
    "whoop": {
      "connected": true,
      "external_user_id": "123",
      "status": "active",
      "last_sync_at": "2026-05-24T12:00:00Z"
    },
    "remarkable": { "adapter": "manual", "last_upload_status": "not_persisted" }
  }
}
```

### GET /whoop/oauth/start

Builds a WHOOP OAuth authorization URL.

Request:

```bash
curl "$BASE/whoop/oauth/start"
```

Response:

```json
{
  "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth?...",
  "state": "abc12345",
  "scopes": [
    "offline",
    "read:workout",
    "read:sleep",
    "read:recovery",
    "read:profile"
  ]
}
```

### GET /whoop/oauth/callback

Exchanges an OAuth code for tokens, fetches WHOOP profile, and stores a source account.

Query params:

| Param   | Required | Description                                    |
| ------- | -------: | ---------------------------------------------- |
| `code`  |      yes | OAuth code from WHOOP redirect                 |
| `state` |      yes | OAuth state from `/whoop/oauth/start` response |

Request:

```bash
curl "$BASE/whoop/oauth/callback?code=WHOOP_CODE&state=WHOOP_STATE"
```

Response:

```json
{
  "source": "whoop",
  "external_user_id": "123",
  "display_name": "Praty",
  "status": "active",
  "last_sync_at": null
}
```

Missing or invalid `state` is rejected. State values are one-time-use.

### GET /whoop/status

Lists WHOOP configuration and connected accounts without exposing tokens.

Request:

```bash
curl "$BASE/whoop/status"
```

Response:

```json
{
  "configured": true,
  "accounts": [
    {
      "external_user_id": "123",
      "display_name": "Praty",
      "status": "active",
      "connected_at": "2026-05-24T12:00:00Z",
      "last_sync_at": "2026-05-24T12:30:00Z",
      "token_expires_at": "2026-05-24T13:00:00Z",
      "scopes": [
        "offline",
        "read:workout",
        "read:sleep",
        "read:recovery",
        "read:profile"
      ]
    }
  ]
}
```

### POST /whoop/sync

Fetches WHOOP workouts, sleeps, and recoveries for an inclusive local date range, normalizes them into `source_events`, and optionally recomputes affected months.

Query params:

| Param              | Required | Default | Description                               |
| ------------------ | -------: | ------: | ----------------------------------------- |
| `external_user_id` |      yes |         | WHOOP user id stored by OAuth callback    |
| `start`            |      yes |         | Inclusive `YYYY-MM-DD` start date         |
| `end`              |      yes |         | Inclusive `YYYY-MM-DD` end date           |
| `recompute`        |       no |  `true` | Recompute months touched by synced events |

Request:

```bash
curl -X POST "$BASE/whoop/sync?external_user_id=$WHOOP_USER_ID&start=$START&end=$END"
```

Response:

```json
{
  "external_user_id": "123",
  "start": "2026-05-01",
  "end": "2026-05-31",
  "workouts": 8,
  "sleeps": 28,
  "recoveries": 27,
  "events_written": 63,
  "recomputed_months": ["2026-05"],
  "written": {
    "workouts": { "inserted": 0, "updated": 8 },
    "sleeps": { "inserted": 0, "updated": 28 },
    "recoveries": { "inserted": 0, "updated": 27 }
  }
}
```

Unauthorized WHOOP tokens return a clear `401` diagnostic and should be fixed by re-running OAuth.

### GET /events

Lists normalized source events for debugging.

Query params:

| Param        | Required | Description                                      |
| ------------ | -------: | ------------------------------------------------ |
| `month`      |       no | `YYYY-MM`; mutually exclusive with `start`/`end` |
| `source`     |       no | e.g. `whoop`, `manual`                           |
| `event_type` |       no | e.g. `workout`, `sleep`, `recovery`              |
| `start`      |       no | Inclusive local date lower bound                 |
| `end`        |       no | Inclusive local date upper bound                 |
| `limit`      |       no | default `100`, max `1000`                        |

Request:

```bash
curl "$BASE/events?source=whoop&event_type=workout&start=$START&end=$END"
```

Response:

```json
[
  {
    "id": "whoop:workout-1",
    "source": "whoop",
    "event_type": "workout",
    "local_date": "2026-05-02",
    "title": "Workout"
  }
]
```

### POST /events/import-sample

Compatibility/debug route that imports `data/sample_events.json`.

Request:

```bash
curl -X POST "$BASE/events/import-sample"
```

Response:

```json
{ "month": "2026-05", "habits": 6, "events": 24, "overrides": 1 }
```

### GET /habit-entries

Returns persisted habit entries for a month.

Query params:

| Param   | Required | Description |
| ------- | -------: | ----------- |
| `month` |      yes | `YYYY-MM`   |

Request:

```bash
curl "$BASE/habit-entries?month=$MONTH"
```

Response:

```json
[
  {
    "date": "2026-05-02",
    "habit_key": "workout",
    "status": "checked",
    "source": "whoop",
    "summary": "42 min workout"
  }
]
```

### POST /habits/recompute

Runs the rule engine for a month and rewrites `habit_entries` for that month.
Manual overrides are preserved by reapplying them from `manual_overrides`.
Operationally, recompute replaces auto-generated entries and then reapplies
manual overrides as the final source of truth.

Query params:

| Param   | Required | Description |
| ------- | -------: | ----------- |
| `month` |      yes | `YYYY-MM`   |

Request:

```bash
curl -X POST "$BASE/habits/recompute?month=$MONTH"
```

Response:

```json
{
  "month": "2026-05",
  "habits": 6,
  "events": 63,
  "overrides": 0,
  "entries_deleted": 120,
  "entries_written": 120
}
```

### GET /state/month

Assembles `MonthHabitState` on read from active habits plus `habit_entries`. No month snapshot is persisted.

Query params:

| Param   | Required | Description |
| ------- | -------: | ----------- |
| `month` |      yes | `YYYY-MM`   |

Request:

```bash
curl "$BASE/state/month?month=$MONTH"
```

Response:

```json
{
  "month": "2026-05",
  "habits": [
    { "key": "workout", "label": "Workout", "short": "WO", "kind": "auto" }
  ],
  "entries": [],
  "generated_at": "2026-05-24T12:00:00Z"
}
```

### POST /render/month

Renders a month PDF from derived `MonthHabitState` and records a `RenderJob`.

Query params:

| Param   | Required | Description |
| ------- | -------: | ----------- |
| `month` |      yes | `YYYY-MM`   |

Request:

```bash
curl -X POST "$BASE/render/month?month=$MONTH"
```

Response:

```json
{
  "id": "665...",
  "month": "2026-05",
  "status": "completed",
  "output_path": "data/generated/2026-05-habit-dashboard.pdf",
  "triggered_by": "manual"
}
```

Render job statuses are standardized to: `pending`, `running`, `completed`, `failed`.

### GET /render/jobs

Lists recent render jobs, newest first.

Query params:

| Param   | Required | Default | Description |
| ------- | -------: | ------: | ----------- |
| `limit` |       no |    `50` | Max `200`   |

Request:

```bash
curl "$BASE/render/jobs?limit=10"
```

Response:

```json
[{ "id": "665...", "month": "2026-05", "status": "completed" }]
```

### GET /render/latest

Returns the most recent render job. Optional `month=YYYY-MM` filters to the
latest render job for that month.

Request:

```bash
curl "$BASE/render/latest"
curl "$BASE/render/latest?month=$MONTH"
```

Response:

```json
{ "id": "665...", "month": "2026-05", "status": "completed" }
```

Returns `404` if there are no render jobs.

### GET /remarkable/status

Shows the current reMarkable adapter and latest render context.

Request:

```bash
curl "$BASE/remarkable/status"
```

Response:

```json
{
  "configured": true,
  "adapter": "manual",
  "mode": "manual_upload",
  "dry_run_supported": true,
  "machine_owned_root": "HabitOS",
  "latest_render_job": null,
  "safety": "Uploads target only generated HabitOS PDFs under HabitOS/00 Current or HabitOS/YYYY/Archive."
}
```

### GET /remarkable/paths

Returns the machine-owned current and archive targets for a month.

Request:

```bash
curl "$BASE/remarkable/paths?month=$MONTH"
```

Response:

```json
{
  "month": "2026-05",
  "current": {
    "name": "00 Current Month - 2026-05 Habit Dashboard",
    "path": "HabitOS/00 Current/00 Current Month - 2026-05 Habit Dashboard.pdf"
  },
  "archive": {
    "name": "2026-05 Habit Dashboard",
    "path": "HabitOS/2026/Archive/2026-05 Habit Dashboard.pdf"
  },
  "machine_owned_root": "HabitOS"
}
```

### POST /remarkable/upload

Returns instructions for uploading the latest completed month PDF to a machine-owned reMarkable path.

Query params:

| Param     | Required | Default | Description                                   |
| --------- | -------: | ------: | --------------------------------------------- |
| `month`   |      yes |         | `YYYY-MM`                                     |
| `dry_run` |       no |  `true` | Generate instructions without device mutation |
| `update`  |       no | `false` | Ask adapter to update instead of upload       |

Request:

```bash
curl -X POST "$BASE/remarkable/upload?month=$MONTH&dry_run=true"
```

Response:

```json
{
  "adapter": "manual",
  "action": "upload",
  "dry_run": true,
  "target_path": "HabitOS/00 Current/00 Current Month - 2026-05 Habit Dashboard.pdf",
  "status": "manual_required",
  "device_mutated": false,
  "message": "Manual upload instructions generated. No files were modified on the reMarkable device.",
  "instructions": ["Confirm the generated PDF exists locally: ..."]
}
```

With the manual adapter, `dry_run=false` still returns manual instructions,
`status: manual_required`, and `device_mutated: false`. It does not perform
automatic upload.

### POST /remarkable/sync

Compatibility alias for `/remarkable/upload` with the same query params and response.

Request:

```bash
curl -X POST "$BASE/remarkable/sync?month=$MONTH&dry_run=true"
```

### GET /remarkable/instructions

Compatibility route that always returns dry-run manual upload instructions.

Query params:

| Param   | Required | Description |
| ------- | -------: | ----------- |
| `month` |      yes | `YYYY-MM`   |

Request:

```bash
curl "$BASE/remarkable/instructions?month=$MONTH"
```

### POST /pipeline/month

Runs the full manual month pipeline.

Steps:

1. WHOOP sync for date range with `recompute=false`.
2. Habit recompute for `month`.
3. Render month PDF.
4. If `upload=true`, run reMarkable upload/sync.
5. Return a structured summary.

Query params:

| Param              | Required | Default | Description                            |
| ------------------ | -------: | ------: | -------------------------------------- |
| `external_user_id` |      yes |         | WHOOP user id                          |
| `start`            |      yes |         | Inclusive `YYYY-MM-DD`                 |
| `end`              |      yes |         | Inclusive `YYYY-MM-DD`                 |
| `month`            |      yes |         | `YYYY-MM` to recompute/render          |
| `upload`           |       no | `false` | Attempt reMarkable upload after render |
| `dry_run`          |       no |  `true` | Passed to reMarkable upload            |

Request:

```bash
curl -X POST "$BASE/pipeline/month?external_user_id=$WHOOP_USER_ID&start=$START&end=$END&month=$MONTH&upload=false"
```

Response:

```json
{
  "range": { "start": "2026-05-01", "end": "2026-05-31", "month": "2026-05" },
  "whoop": {
    "workouts": { "inserted": 0, "updated": 8 },
    "sleeps": { "inserted": 0, "updated": 28 },
    "recoveries": { "inserted": 0, "updated": 27 },
    "events_written": 63
  },
  "habits": {
    "recomputed": 120,
    "month": "2026-05",
    "entries_deleted": 120,
    "events": 63,
    "overrides": 0
  },
  "render": {
    "status": "completed",
    "job_id": "665...",
    "pdf_path": "data/generated/2026-05-habit-dashboard.pdf"
  },
  "remarkable": { "attempted": false, "status": "skipped" }
}
```

If rendering fails, upload is skipped and the response is a `500` with a summary showing `render.status = failed` and `remarkable.status = skipped`.

If upload fails, the endpoint still returns the rendered PDF path and reports `remarkable.status = failed`.

### GET /automation/status

Reports scheduler configuration, resolved automation settings, and the latest persisted automation run.

Request:

```bash
curl "$BASE/automation/status"
```

Response:

```json
{
  "scheduler": {
    "enabled": false,
    "running": false,
    "next_run_at": null
  },
  "timezone": "America/New_York",
  "reconcile_days": 14,
  "default_whoop_external_user_id_configured": true,
  "auto_upload_remarkable": false,
  "remarkable_dry_run": true,
  "latest_run": null
}
```

### POST /automation/nightly-run

Manually invokes the nightly automation pipeline using the configured default WHOOP external user id.

Query params:

| Param     | Required | Default | Description                                 |
| --------- | -------: | ------: | ------------------------------------------- |
| `dry_run` |       no |  `true` | Passed through to reMarkable lifecycle prep |

Request:

```bash
curl -X POST "$BASE/automation/nightly-run?dry_run=true"
```

Response shape:

```json
{
  "run_id": "665...",
  "run_type": "manual",
  "date": "2026-06-10",
  "timezone": "America/New_York",
  "window": {
    "start": "2026-05-27",
    "end": "2026-06-10",
    "reconcile_days": 14
  },
  "months": {
    "current": "2026-06",
    "previous": null,
    "affected": ["2026-05", "2026-06"]
  },
  "rollover": { "detected": false },
  "whoop": {},
  "habits": [],
  "render": {},
  "remarkable": {}
}
```

### POST /automation/month-rollover

Forces month-rollover behavior explicitly.

Query params:

| Param        | Required | Description              |
| ------------ | -------: | ------------------------ |
| `from_month` |      yes | `YYYY-MM` previous month |
| `to_month`   |      yes | `YYYY-MM` next month     |
| `dry_run`    |       no | `true` by default        |

Request:

```bash
curl -X POST "$BASE/automation/month-rollover?from_month=2026-05&to_month=2026-06&dry_run=true"
```

Returns render summaries for both months plus current/archive reMarkable lifecycle preparation details.

## Idempotency

- WHOOP sync is safe to rerun for the same range/user.
- `source_events` are upserted by `(source, source_event_id)`, so reruns update
  existing events instead of duplicating them.
- `MonthHabitState` is derived on read from active habits plus persisted
  `habit_entries`; it is not stored as a month snapshot.
- Render jobs are append-only audit records, while generated PDFs are
  machine-owned artifacts that can be regenerated.
