# HabitOS

A small, local-first habit dashboard generator that turns tracker data into a
calm, hyperlinked monthly PDF for **reMarkable 2**.

This repository now has the local MVP pipeline plus early integrations:

> sample/WHOOP-style events → habit entries → rendered monthly PDF → manual reMarkable 2 sync instructions.

WHOOP import and reMarkable sync are intentionally small and manual-first. The reMarkable adapter does not mutate device or cloud state; it returns safe upload instructions for generated, machine-owned PDFs. Muse, Apple Health, automated USB/cloud sync, and admin UI remain future work.
See [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) for the full plan.

---

## Quickstart

Requirements: Python 3.11+, internet access to download a Chromium binary the
first time (Playwright uses it to print HTML → PDF).

```bash
make setup          # create .venv, install deps, download Chromium
make render-sample  # render data/sample_month.json
```

The PDF is written to:

```text
data/generated/2026-05-habit-dashboard.pdf
```

A debug HTML twin is written alongside it.

To run the smoke tests:

```bash
make test
```

## Persistence

The renderer (Milestone 1) and rule engine (Milestone 2) work on local JSON
and need no database. From Milestone 3 onward HabitOS persists everything in
**MongoDB** — Atlas in production, a local Mongo for dev. Configuration via
`.env` (copy `.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `MONGODB_URI` | Connection string | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Database name | `habitos` |
| `MONGODB_TEST_URI` | Used by repository integration tests; tests auto-skip when unset | _(unset)_ |

The driver is **PyMongo Async** (`pymongo>=4.9`, `AsyncMongoClient`). Motor
is not used. Migrations are not used either — indexes are declared in
`packages/core/indexes.py` and applied idempotently at app startup via
`ensure_indexes()`.

Collection design and index rationale: see [docs/persistence.md](docs/persistence.md).

## Running the API (Milestone 3)

Once `.env` is set up and a MongoDB is reachable:

```bash
make run-api      # uvicorn apps.api.main:app --reload on 127.0.0.1:8000
```

Quick end-to-end smoke test against the sample data:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/events/import-sample
curl    "http://127.0.0.1:8000/events?month=2026-05"
curl -X POST "http://127.0.0.1:8000/habits/recompute?month=2026-05"
curl    "http://127.0.0.1:8000/habit-entries?month=2026-05"
curl    "http://127.0.0.1:8000/state/month?month=2026-05"
curl -X POST "http://127.0.0.1:8000/render/month?month=2026-05"
curl    "http://127.0.0.1:8000/render/latest"
curl    "http://127.0.0.1:8000/render/jobs"
```

Or browse the interactive docs at <http://127.0.0.1:8000/docs>.

### Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + Mongo ping |
| GET | `/events?month=&source=&limit=` | List ingested source events |
| POST | `/events/import-sample` | Ingest `data/sample_events.json` into Mongo |
| GET | `/habit-entries?month=YYYY-MM` | Stored, resolved entries for a month |
| POST | `/habits/recompute?month=YYYY-MM` | Run the rule engine and persist entries |
| GET | `/state/month?month=YYYY-MM` | `MonthHabitState` assembled from entries (derived, never stored) |
| POST | `/render/month?month=YYYY-MM` | Render a PDF; records a `RenderJob` |
| GET | `/render/jobs?limit=` | Recent render jobs |
| GET | `/render/latest` | Most recent render job |
| GET | `/remarkable/instructions?month=YYYY-MM` | Manual upload instructions for latest rendered month PDF |
| POST | `/remarkable/sync?month=YYYY-MM&dry_run=true` | Manual reMarkable sync adapter result; no device/cloud mutation |

Indexes are applied idempotently on startup via `ensure_indexes()`.

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

---

## Design choices

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

The current sync path is still manual-first and safe. HabitOS can now generate
manual upload instructions for the latest completed render job:

```bash
curl "http://127.0.0.1:8000/remarkable/instructions?month=2026-05"
```

The target naming convention is machine-owned:

```text
HabitOS / YYYY / YYYY-MM Habit Dashboard.pdf
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

## Integration architecture

HabitOS has a formal integration contract for adding new services (Muse, Day
One, Apple Health, medication trackers, future wearables). New integrations
normalize into `SourceEvent`, never write `habit_entries` directly, and plug
into the nightly automation pipeline through a typed sync summary.

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

WHOOP is the reference connector. It predates the formal contract; the
blueprint documents the migration path without forcing a refactor now.

---

## Project layout

```text
packages/renderer/
  render_month.py            # entrypoint: JSON → HTML → PDF
  links.py                   # anchor name helpers
  templates/
    base.html
    month.html
    week.html
    day.html
  static/
    remarkable.css           # grayscale, e-ink-friendly stylesheet

data/
  sample_month.json          # one fake month of habit data
  generated/                 # output; gitignored except .gitkeep

tests/
  test_render_smoke.py
```

---

## Sample data format

`data/sample_month.json` is the single source for Milestone 1. The shape:

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

---

## What is intentionally not here

- Real connectors (WHOOP, Muse, Apple Health, Calendar).
- A backend API, database, or scheduler.
- Automatic sync to reMarkable.
- An admin / debug UI.
- A habit rule engine.

Those are scheduled for later milestones. The point of Milestone 1 is a single
beautiful artifact you can hold in your hand.
