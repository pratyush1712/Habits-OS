# HabitOS

A small, local-first habit dashboard generator that turns tracker data into a
calm, hyperlinked monthly PDF for **reMarkable 2**.

The full pipeline is wired end to end:

> WHOOP + Day One + manual events → normalized `source_events` → habit rule engine → persisted `habit_entries` → rendered monthly PDF → manual or automated reMarkable sync.

A nightly APScheduler job reconciles a rolling window, recomputes touched
months, renders the current month, and (optionally) pushes the PDF to the
reMarkable Cloud via [`ddvk/rmapi`](https://github.com/ddvk/rmapi). The
manual reMarkable adapter remains the default — it never mutates device or
cloud state, only returns upload instructions.

See [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) for the full plan.

---

## Quickstart

Requirements: Python 3.11+, a reachable MongoDB (local or Atlas), and internet
access to download a Chromium binary the first time (Playwright uses it to
print HTML → PDF).

```bash
make setup          # create .venv, install deps, download Chromium
make render-sample  # render data/sample_month.json (no DB required)
make test
```

`make render-sample` writes:

```text
data/generated/2026-05-habit-dashboard.pdf
```

A debug HTML twin is written alongside it. The renderer and rule engine work
on local JSON and need no database — only the API and connectors do.

To evaluate rules against sample events without the API:

```bash
make evaluate-sample
```

---

## Configuration

Copy `.env.example` to `.env` and fill in what you need. The full set of
variables is documented inline; the essentials are:

| Variable                                                         | Purpose                                                          | Default                     |
| ---------------------------------------------------------------- | ---------------------------------------------------------------- | --------------------------- |
| `MONGODB_URI`                                                    | Mongo connection string                                          | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME`                                                | Database name                                                    | `habitos`                   |
| `MONGODB_TEST_URI`                                               | Used by repository integration tests; tests auto-skip when unset | _(unset)_                   |
| `HABITOS_TIMEZONE`                                               | IANA tz for local date resolution + scheduler                    | `EST`                       |
| `HABITOS_OUTPUT_DIR`                                             | Where the renderer writes PDFs                                   | `data/generated`            |
| `HABITOS_SCHEDULER_ENABLED`                                      | Turn the nightly APScheduler job on/off                          | `false`                     |
| `HABITOS_NIGHTLY_RUN_HOUR` / `_MINUTE`                           | Local time the nightly job fires                                 | `3` / `0`                   |
| `HABITOS_RECONCILE_DAYS`                                         | Rolling WHOOP/Day One reconciliation window                      | `14`                        |
| `HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID`                         | Default WHOOP user id for automation                             | _(unset)_                   |
| `HABITOS_AUTO_UPLOAD_REMARKABLE`                                 | Nightly job also uploads to reMarkable                           | `false`                     |
| `HABITOS_REMARKABLE_ADAPTER`                                     | `manual` (default, safe) or `rmapi`                              | `manual`                    |
| `WHOOP_CLIENT_ID` / `WHOOP_CLIENT_SECRET` / `WHOOP_REDIRECT_URI` | WHOOP OAuth app credentials                                      | —                           |
| `DAYONE_DB_PATH`                                                 | Path to Day One SQLite; empty disables the integration cleanly   | _(unset)_                   |

rmapi-specific variables (`HABITOS_RMAPI_BINARY`, `HABITOS_RMAPI_CONFIG_PATH`,
`HABITOS_RMAPI_REPLACE_EXISTING_CURRENT`, `HABITOS_REMARKABLE_MACHINE_ROOT`,
…) live in `.env.example` and
[docs/remarkable_sync.md](docs/remarkable_sync.md#automated-adapter-rmapi).

## Persistence

Everything from Milestone 3 onward persists in **MongoDB**. The driver is
**PyMongo Async** (`pymongo>=4.9`, `AsyncMongoClient`) — Motor is not used.
There are no migrations; indexes are declared in `packages/core/indexes.py`
and applied idempotently at app startup via `ensure_indexes()`.

Collections currently in use:

- `source_events` — normalized events from WHOOP, Day One, manual import
- `habit_entries` — resolved per-day habit results
- `habits` — habit catalog (seeded with defaults on startup)
- `manual_overrides` — user overrides that take priority over rules
- `source_accounts` — connected accounts and encrypted tokens
- `render_jobs` — append-only log of PDF renders
- `automation_runs` — append-only log of nightly/manual/rollover pipeline runs

Collection design and index rationale: see [docs/persistence.md](docs/persistence.md).

---

## Running the API

```bash
make run-api      # uvicorn apps.api.main:app --reload on 127.0.0.1:8000
```

Browse interactive docs at <http://127.0.0.1:8000/docs>, or use the curl
recipes in [docs/api.md](docs/api.md).

### Routes

| Method | Path                                               | Purpose                                                          |
| ------ | -------------------------------------------------- | ---------------------------------------------------------------- |
| GET    | `/health`                                          | Liveness + Mongo ping                                            |
| GET    | `/status`                                          | Mongo, integrations, latest render & sync summary                |
| GET    | `/events?month=&source=&limit=`                    | List ingested source events                                      |
| POST   | `/events/import-sample`                            | Ingest `data/sample_events.json` into Mongo                      |
| GET    | `/habits`                                          | List habit catalog                                               |
| POST   | `/habits/seed-defaults`                            | Re-seed default habits                                           |
| POST   | `/habits/recompute?month=YYYY-MM`                  | Run the rule engine and persist entries                          |
| GET    | `/habit-entries?month=YYYY-MM`                     | Stored, resolved entries for a month                             |
| GET    | `/state/month?month=YYYY-MM`                       | `MonthHabitState` assembled from entries (derived, never stored) |
| POST   | `/render/month?month=YYYY-MM`                      | Render a PDF; records a `RenderJob`                              |
| GET    | `/render/jobs?limit=`                              | Recent render jobs                                               |
| GET    | `/render/latest`                                   | Most recent render job                                           |
| GET    | `/remarkable/status`                               | Selected adapter + recent upload summary                         |
| GET    | `/remarkable/paths?month=YYYY-MM`                  | Current/archive target paths for a month                         |
| GET    | `/remarkable/instructions?month=YYYY-MM`           | Manual upload instructions                                       |
| POST   | `/remarkable/sync?month=YYYY-MM&dry_run=true`      | Adapter-driven sync (manual = instructions only)                 |
| POST   | `/remarkable/upload?month=YYYY-MM&dry_run=true`    | Adapter upload entry point used by automation                    |
| GET    | `/whoop/oauth/start`                               | Begin WHOOP OAuth, returns authorization URL                     |
| GET    | `/whoop/oauth/callback`                            | OAuth callback; stores a `SourceAccount`                         |
| GET    | `/whoop/status`                                    | Connected accounts, last sync, token freshness                   |
| POST   | `/whoop/sync?external_user_id=&start=&end=`        | Manual WHOOP date-range sync                                     |
| GET    | `/dayone/status`                                   | Day One DB reachability + last sync                              |
| POST   | `/dayone/sync?start=&end=`                         | Manual Day One sync (metadata-only by default)                   |
| POST   | `/pipeline/month?...`                              | Run WHOOP→recompute→render (+ optional upload) for one month     |
| GET    | `/automation/status`                               | Scheduler state + recent `automation_runs`                       |
| POST   | `/automation/nightly-run?dry_run=true`             | Trigger the nightly pipeline manually                            |
| POST   | `/automation/month-rollover?from_month=&to_month=` | Force a rollover                                                 |

---

## Nightly automation

When `HABITOS_SCHEDULER_ENABLED=true`, an in-process APScheduler job runs at
the configured local time and:

1. Reconciles WHOOP for a rolling `HABITOS_RECONCILE_DAYS` window.
2. If `DAYONE_DB_PATH` is set, reconciles Day One for the same window
   (metadata-only; missing path is a clean skip, not a failure).
3. Recomputes every month touched by the union of those syncs.
4. Renders the current-month PDF.
5. Optionally uploads it to reMarkable via the selected adapter.
6. On the 1st of the month, finalizes and archives the previous month.

Every run is persisted in `automation_runs` and surfaced via
`GET /automation/status`. Full details and safety model:
[docs/automation.md](docs/automation.md).

### Running it as a background service

`scripts/run_habitos_api.sh` is the launchd-friendly entrypoint (sets
`SSL_CERT_FILE` from `certifi` so Mongo Atlas TLS works under launchd).
`scripts/restart_service.sh` and `scripts/update_service.sh` wrap the
common ops:

```bash
make service-restart   # kickstart the launchd job, then ping /health
make service-update    # git pull + make setup + restart
make service-logs      # tail ~/Library/Logs/HabitOS/api.{out,err}.log
make service-status    # launchctl print of the job
```

These assume a launchd plist labeled `com.pratyush.habitos.api`; adjust the
scripts for your own setup.

---

## What the PDF contains

A single, portrait-oriented document sized for reMarkable 2 (157 × 210 mm),
containing in order:

1. **Monthly dashboard** — a 7-column calendar grid. Each day cell shows the
   day number and a row of small status glyphs (one per habit). Tapping a day
   jumps to that day's detail page. A footer legend lists the habits, status
   meanings, and links to each weekly review page.
2. **Weekly review pages** — one per calendar row in the month. Per-habit
   counts, a list of the week's days (each tappable), an "intention" line
   block, and a tall "reflection" line block for handwriting.
3. **Daily detail pages** — one per day. A habit table with status, summary,
   and (where present) extended details, plus a tall blank line block for
   notes. Each page has a back link to the month dashboard, the parent week,
   and prev/next day.

All links are PDF internal anchors, so they work on the device without any
network connection.

### Design choices

- **Grayscale only.** Status is conveyed by glyph shape (●, ◐, △, ○, ◆), never
  by color.
- **Generous tap targets.** Day cells in the grid are ≥ ~20 mm tall; back
  links are bordered chips with padding.
- **Handwriting space.** Every day and week page has a ruled block sized for
  finger or stylus writing.
- **Single HTML document.** Internal anchors are preserved into the PDF by
  Chromium's print pipeline, which keeps the pipeline boring.

---

## Putting the PDF onto a reMarkable 2

The default sync path is still manual-first and safe. Ask for the upload
instructions for the latest completed render job:

```bash
curl "http://127.0.0.1:8000/remarkable/instructions?month=2026-05"
```

The target naming convention is machine-owned:

```text
HabitOS/00 Current/00 Current Month - YYYY-MM Habit Dashboard.pdf       # current
HabitOS/YYYY/Archive/YYYY-MM Habit Dashboard.pdf                        # archived
```

Then either:

1. Plug the tablet in over USB, enable the USB web interface in **Settings →
   Storage**, open `http://10.11.99.1/`, and upload the PDF; **or**
2. Email the PDF to yourself and open it in the reMarkable mobile app to
   send it to the tablet; **or**
3. Use the reMarkable desktop app's "Send to reMarkable" flow.

The manual adapter never overwrites handwritten notebooks and does not touch
reMarkable device/cloud state.

### Automated cloud sync (optional, via rmapi)

HabitOS ships an `rmapi` adapter that pushes generated PDFs to the
reMarkable Cloud non-interactively, gated behind a folder allowlist and a
conservative replace policy. It uses the actively-maintained
[ddvk/rmapi](https://github.com/ddvk/rmapi) CLI. Setup, env vars,
safety model, and troubleshooting are in
[docs/remarkable_sync.md](docs/remarkable_sync.md#automated-adapter-rmapi).

Switch on with `HABITOS_REMARKABLE_ADAPTER=rmapi` after installing and
authenticating rmapi locally. The default remains `manual`.

---

## Integrations

| Integration            | Status                                       | Notes                                                                                          |
| ---------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| WHOOP                  | ✅ OAuth, manual + nightly sync              | Workouts, sleep, recovery. See [docs/whoop_integration.md](docs/whoop_integration.md).         |
| Day One                | ✅ Local SQLite, metadata-only by default    | Drives the `journaling` habit. See [docs/integrations/dayone.md](docs/integrations/dayone.md). |
| Manual / sample events | ✅ `/events/import-sample`, sample fixtures  | —                                                                                              |
| reMarkable (manual)    | ✅ Upload instructions, never mutates device | Default adapter.                                                                               |
| reMarkable (rmapi)     | ✅ Cloud sync via ddvk/rmapi                 | Folder allowlist, replace gated by env var.                                                    |
| Muse / Apple Health    | ⏳ Not started                               | Sketch in [docs/integration_examples.md](docs/integration_examples.md).                        |
| Admin / debug UI       | ⏳ Not started                               | Optional, debug-only when added.                                                               |

### Integration architecture

HabitOS has a formal integration contract for adding new services. New
integrations normalize into `SourceEvent`, never write `habit_entries`
directly, and plug into the nightly automation pipeline through a typed
sync summary.

Start here:

- [docs/integration_blueprint.md](docs/integration_blueprint.md) — philosophy,
  pipeline mapping, and the Automation Compatibility Contract.
- [docs/integration_template.md](docs/integration_template.md) — fill-in-the-
  blanks template every new integration doc must use.
- [docs/integration_examples.md](docs/integration_examples.md) — sketches for
  Muse, Day One, Apple Health, and a medication tool.
- [docs/new_integration_agent_prompt.md](docs/new_integration_agent_prompt.md)
  — copy-paste prompt for spawning a sub-agent that adds one.
- [docs/automation.md](docs/automation.md) — how the nightly pipeline calls
  integrations today and what status it exposes.
- [`packages/connectors/base.py`](packages/connectors/base.py) — the typed
  contract (`ConnectorCapability`, `IntegrationSyncSummary`, `BaseConnector`).

WHOOP predates the formal contract; the blueprint documents the migration
path without forcing a refactor now.

---

## Project layout

```text
apps/
  api/
    main.py                  # FastAPI app + lifespan (Mongo, indexes, scheduler)
    config.py                # env-driven Settings
    deps.py                  # request-scoped dependency factories
    errors.py
    scheduler.py             # APScheduler builder
    routes/                  # health, status, events, habits, habit_entries,
                             # state, render, remarkable_sync, whoop, dayone,
                             # pipeline, automation
    services/                # ingestion, evaluation, render, pipeline,
                             # automation, *_sync, remarkable_lifecycle, …

packages/
  core/
    models.py                # Pydantic boundary models
    rules.py                 # pure habit rule functions
    evaluate.py              # in-process JSON-only evaluator (CLI)
    config.py
    db.py                    # AsyncMongoClient factory
    indexes.py               # ensure_indexes()
    default_habits.py
    repositories/            # only layer that touches Mongo
  connectors/
    base.py                  # ConnectorCapability, IntegrationSyncSummary
    whoop/                   # auth, client, normalizer, webhook
    dayone/                  # config, sqlite_reader, normalizer
  renderer/
    render_month.py          # entrypoint: JSON/state → HTML → PDF
    links.py
    templates/{base,month,week,day}.html
    static/remarkable.css
  remarkable_sync/
    base.py                  # adapter interface
    manual.py                # default; returns upload instructions only
    rmapi.py                 # ddvk/rmapi adapter

scripts/                     # launchd helpers (run/restart/update)

data/
  sample_month.json          # one fake month for the renderer
  sample_events.json         # one fake month of source_events for the API
  generated/                 # PDF output; gitignored except .gitkeep

tests/
  core/  connectors/  api/  sync/  test_render_smoke.py
```

---

## Sample data format

`data/sample_month.json` drives Milestone 1's renderer directly:

```jsonc
{
  "month": "2026-05",
  "habits": [
    {"key": "workout", "label": "Workout", "short": "W"},
    ...
  ],
  "days": [
    {
      "date": "2026-05-01",
      "entries": [
        {
          "habit_key": "workout",
          "status": "checked",       // checked | partial | warning | missed | manual
          "summary": "45m run",
          "description": "optional longer note"
        }
      ]
    }
  ]
}
```

Days missing from the file render as empty (no status glyphs). Invalid
statuses cause the renderer to raise.

`data/sample_events.json` drives the rule engine and the API
`/events/import-sample` route.

---

## What is intentionally not here yet

- Muse SDK / raw EEG ingestion (kept off the MVP critical path).
- Apple Health HealthKit bridge (sketched, not implemented).
- An admin / debug UI — scaffold and architecture decisions are in
  [docs/web_dashboard_setup.md](docs/web_dashboard_setup.md); implementation
  happens in Cursor under `apps/admin/`.
- WHOOP webhook receivers (the signature helper exists; nightly pull is the
  current source of truth).
- SSH-based reMarkable sync (deliberately avoided; rmapi cloud sync covers
  the automation use case).

These follow Milestone 7+. The north star remains: a calm reMarkable 2
dashboard that quietly reflects what the user already did.
