# HabitOS

A small, local-first habit dashboard generator that turns tracker data into a
calm, hyperlinked monthly PDF for **reMarkable 2**.

This repository is currently at **Milestone 1**:

> Fake/sample JSON → beautiful hyperlinked monthly PDF for reMarkable 2,
> uploaded manually.

No WHOOP, Muse, Apple Health, backend API, sync automation, or admin UI yet.
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

For now this is manual. Either:

1. Plug the tablet in over USB, enable the USB web interface in **Settings →
   Storage**, open `http://10.11.99.1/`, and drag the PDF in; **or**
2. Email the PDF to yourself and open it in the reMarkable mobile app to
   send it to the tablet; **or**
3. Use the reMarkable desktop app's "Send to reMarkable" flow.

Sync automation (`rmcl`/`rmapi`) is intentionally out of scope for this
milestone.

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
