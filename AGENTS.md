# AGENTS.md

_Last updated: 2026-05-25_

This file defines the agent plan for **HabitOS**, a small local-first personal automation system that turns tracker activity into a beautiful monthly habit dashboard for **reMarkable 2**.

The goal is not to build a giant productivity platform. The goal is to make the user's existing behavior visible with as little manual effort as possible.

> **Current implementation status (2026-05-25).** Milestones 1–5 are complete
> and wired together end-to-end:
>
> - ✅ M1 Static PDF renderer (`packages/renderer/`)
> - ✅ M2 Pydantic models + pure rule engine (`packages/core/`)
> - ✅ M3 FastAPI + MongoDB orchestration (`apps/api/`, `packages/core/repositories/`)
>   plus a nightly APScheduler job, `automation_runs` history, and launchd
>   scripts under `scripts/`
> - ✅ M4 WHOOP OAuth + pull-based reconciliation (`packages/connectors/whoop/`)
> - ✅ M5 reMarkable sync: manual instructions adapter (default, safe) plus an
>   optional `ddvk/rmapi` cloud adapter (`packages/remarkable_sync/`)
> - 🆕 Day One integration (read-only SQLite, metadata-only) was added
>   outside the original milestone list to drive the `journaling` habit
>   (`packages/connectors/dayone/`, [`docs/integrations/dayone.md`](docs/integrations/dayone.md))
> - ⏳ M6 Muse / meditation ingestion — not started
> - ⏳ M7 Admin / debug UI — not started
>
> See [README.md](README.md) for the user-facing surface and
> [docs/api.md](docs/api.md) for the live HTTP routes.

---

## 1. Product philosophy

HabitOS should be:

- **Small before impressive**
- **Useful before automated**
- **Calm before gamified**
- **Local-first and private**
- **reMarkable-centered, but not reMarkable-owned**
- **Pattern-focused, not shame-focused**

The reMarkable 2 should be treated as the **calm output surface**, not the source of truth.

```text
Trackers / APIs / manual imports / medication dose logs
  → connectors
  → normalized source_events
  → habit rule engine
  → habit_entries
  → generated hyperlinked monthly PDF
  → upload/sync to reMarkable 2
```

The backend/database is the source of truth. The generated PDF is a replaceable artifact.

---

## 2. Non-negotiable constraints

1. **Do not build a giant productivity app.**
2. **Do not add a new daily tool the user must maintain.**
3. **Do not start by writing a native reMarkable app.**
4. **Do not directly edit reMarkable notebook internals in v1.**
5. **Do not overwrite human-owned handwritten notebooks.**
6. **Do not make streaks punitive or shame-based.**
7. **Do not store secrets in Git.**
8. **Do not assume reMarkable Paper Pro instructions apply to reMarkable 2.**
9. **Do not implement raw Muse EEG processing in the MVP.**
10. **Do not add SQLAlchemy/Alembic/Postgres/Redis/Celery.** Persistence is MongoDB-only via PyMongo Async — see `docs/persistence.md`.

---

## 3. Current implementation assumptions

### User device

The user has a **reMarkable 2**, not Paper Pro.

For reMarkable 2, prefer:

1. Generated PDF + manual upload first
2. USB web interface if available
3. reMarkable Cloud community tooling such as `rmcl` or `rmapi`
4. SSH/local access only after explicit testing and only as an advanced adapter

### Preferred stack

```text
Backend:
- Python
- FastAPI
- Pydantic
- PyMongo Async (pymongo >= 4.9, AsyncMongoClient)
- MongoDB (local for dev, Atlas for hosted)
- Repository layer under packages/core/repositories/ is the only place
  that touches MongoDB
- No SQLAlchemy, no Alembic, no Postgres, no Motor

Scheduling:
- APScheduler first
- No Redis, RQ, or Celery

PDF:
- HTML/CSS templates
- Playwright print-to-PDF
- Later: ReportLab or Typst if exact PDF control is needed

Admin/debug UI:
- Optional
- Next.js 15
- TypeScript
- Tailwind
- shadcn/ui

reMarkable sync:
- Manual upload first
- USB web interface or rmcl second
- SSH only later

Deployment:
- Local-first
- MongoDB Atlas free tier acceptable for hosted use
- Docker is optional; not required for the database
- Hosted deployment only after local MVP works
```

---

## 4. Documentation references

Agents must refresh relevant docs before implementing service-specific code.

### WHOOP

Official docs:

- API reference: https://developer.whoop.com/api/
- Webhooks: https://developer.whoop.com/docs/developing/webhooks/

Implementation notes:

- WHOOP uses OAuth 2.0 authorization code flow.
- Useful scopes include:
  - `read:workout`
  - `read:sleep`
  - `read:recovery`
  - `read:cycles`
  - `read:profile`
- WHOOP provides workout, sleep, recovery, cycle, body measurement, and profile endpoints.
- WHOOP webhooks should be treated as notifications, not complete data payloads.
- On webhook receipt, fetch the full resource from the WHOOP API.
- Use async processing and reconciliation because webhooks can be duplicated, delayed, or missed.

### Muse

Official docs:

- Muse SDK: https://choosemuse.com/pages/developers
- Muse + Apple Health support: https://choosemuse.my.site.com/s/article/Integrating-Muse-with-Apple-Health

Implementation notes:

- Muse's official developer path is SDK/device-data oriented.
- Do not assume there is a simple personal cloud API for historical meditation sessions.
- For MVP, prefer:
  1. Manual meditation endpoint / shortcut
  2. Apple Health Mindful Minutes import
  3. Muse export import if available
  4. Muse SDK later

### Apple Health / HealthKit

Official docs:

- HealthKit: https://developer.apple.com/documentation/healthkit

Implementation notes:

- Apple Health may be a practical bridge for meditation/mindfulness data if Muse writes Mindful Minutes.
- Direct HealthKit access usually requires an iOS app or export workflow.
- Do not make Apple Health the first blocker unless the user explicitly wants the iOS path.

### reMarkable 2

Official docs:

- Developer documentation: https://developer.remarkable.com/documentation

Community/docs/tools:

- USB web interface guide: https://remarkable.guide/tech/usb-web-interface.html
- SSH guide: https://remarkable.guide/guide/access/ssh.html
- Awesome reMarkable: https://github.com/reHackable/awesome-reMarkable
- rmcl: https://github.com/rschroll/rmcl
- rmapi: https://github.com/juruen/rmapi
- rmapy: https://github.com/subutux/rmapy
- recalendar.js: https://github.com/klimeryk/recalendar.js

Implementation notes:

- Treat generated PDFs as machine-owned artifacts.
- Do not overwrite notebooks containing important handwritten notes.
- Manual upload is acceptable for Milestone 1.
- Cloud libraries are unofficial and may break.
- SSH/local access is powerful but should be isolated behind an adapter and not required for the MVP.

---

## 5. Target repo structure

```text
habitos/
  AGENTS.md
  CLAUDE.md
  README.md
  .env.example
  pyproject.toml
  Makefile

  apps/
    api/
      main.py
      routes/
      services/
      scheduler.py

    admin/
      # Optional Next.js debug UI

  packages/
    core/
      models.py
      rules.py
      config.py
      time.py

    connectors/
      whoop/
        client.py
        auth.py
        webhook.py
        normalizer.py

      meditation/
        manual.py
        apple_health_import.py
        muse_import.py

    renderer/
      render_month.py
      links.py
      templates/
        month.html
        day.html
        week.html
        summary.html
      static/
        remarkable.css

    remarkable_sync/
      base.py
      manual.py
      rmcl_sync.py
      usb_web.py
      ssh_sync.py

  data/
    sample/
      sample_month.json
      sample_events.json
    generated/
      .gitkeep

  tests/
    core/
    connectors/
    renderer/
    sync/

  docs/
    product_requirements.md
    data_model.md
    whoop_integration.md
    meditation_ingestion.md
    remarkable_sync.md
    security_privacy.md
    milestones.md
```

---

## 6. Shared domain model

Agents should use these names consistently.

### `source_events`

Raw or normalized events from external sources.

Fields:

```text
id
source
source_event_id
event_type
start_time_utc
end_time_utc
local_date
timezone
title
description
metrics_json
raw_payload_json
created_at
updated_at
```

### `habit_entries`

Final habit result for one habit on one date.

Fields:

```text
id
date
habit_key
status
source
summary
description
confidence
linked_source_event_ids
manually_overridden
created_at
updated_at
```

### Status enum

```text
checked
partial
warning
missed
manual
```

### Source enum

```text
whoop
muse
apple_health
manual
calendar
github
remarkable
medication
```

### Initial habits

```text
workout
sleep
recovery
meditation
journaling
deep_work
medication
```

---

## 7. Milestones

### Milestone 1 — Static PDF MVP ✅ done

Build a beautiful, hyperlinked monthly reMarkable 2 habit dashboard PDF from fake JSON.

No WHOOP. No Muse. No cloud sync. No admin UI.

Acceptance criteria:

- Monthly grid exists.
- Daily pages exist.
- Clicking a day goes to the daily page.
- Daily page links back to monthly dashboard.
- Habit states render clearly in grayscale.
- PDF is comfortable to read on reMarkable 2.
- Generated file can be manually uploaded to reMarkable 2.

### Milestone 2 — Core state and rule engine ✅ done

Build normalized models and habit evaluation from fake events.

Acceptance criteria:

- Fake WHOOP workout creates checked workout habit.
- Fake short workout creates partial workout habit.
- Fake sleep under target creates warning sleep habit.
- Manual override takes priority.
- Unit tests exist.

### Milestone 3 — Backend orchestration ✅ done

> The shipped surface is `POST /render/month?month=YYYY-MM` (not
> `/render/current-month`); nightly automation handles the implicit
> "current month" flow.

Build FastAPI service that can ingest events, compute habit entries, render current month, and expose a download endpoint.

Acceptance criteria:

- Local API runs.
- MongoDB persists source events, manual overrides, habit entries, render jobs,
  source accounts, and the habit catalog (see `docs/persistence.md`).
- Repositories are the only layer that touches MongoDB.
- `POST /render/current-month` creates PDF.
- `GET /habit-entries?month=YYYY-MM` returns month state assembled from
  `habit_entries` (no separate MonthHabitState snapshots).

### Milestone 4 — WHOOP import ✅ done (pull-based; webhooks deferred)

Add WHOOP OAuth, fetch, normalization, and reconciliation.

Acceptance criteria:

- OAuth flow completes locally.
- Recent workouts, sleep, recovery can be fetched.
- WHOOP records normalize into `source_events`.
- Reconciliation job can refetch recent days.

### Milestone 5 — reMarkable sync ✅ done (manual + rmapi; rmcl/USB not built)

Add manual sync first, then optional rmcl/USB adapter. _Shipped: manual
adapter + ddvk/rmapi cloud adapter. rmcl and the USB web adapter were
not built because rmapi covers the same need._

Acceptance criteria:

- Generated PDF appears in a predictable output folder.
- Manual upload instructions are printed.
- Optional adapter can upload or update machine-owned dashboard PDF.

### Milestone 6 — Meditation import ⏳ not started

Add lowest-friction meditation import.

Acceptance criteria:

- Manual endpoint or Apple Health import can create meditation event.
- Meditation rules convert sessions into habit entries.

### Milestone 7 — Optional admin/debug UI ⏳ not started

Add minimal Next.js UI for inspection and override.

Acceptance criteria:

- Can inspect raw events.
- Can inspect why a habit was checked.
- Can override a habit.
- Can trigger render and sync.

---

## 8. Agent prompts

Each agent must read:

1. This `AGENTS.md`
2. `CLAUDE.md`
3. Relevant docs under `docs/`
4. Relevant source files before editing

Agents must preserve scope boundaries.

---

### Agent 0 — Documentation Research Agent

```text
You are the Documentation Research Agent for HabitOS.

Your job is to collect and summarize the most current implementation-relevant documentation for:
1. WHOOP Developer API
2. WHOOP OAuth and webhook behavior
3. Muse SDK / Muse data export options
4. Apple HealthKit mindfulness/workout/sleep data as a possible Muse bridge
5. reMarkable 2 file transfer/sync options
6. reMarkable Cloud community libraries such as rmcl, rmapi, rmapy
7. reMarkable 2 USB web interface and SSH/local access

Big picture:
HabitOS is a small personal automation system. It ingests tracker data, normalizes it into habit events, generates a hyperlinked monthly PDF, and syncs that PDF to reMarkable 2.

Do not write implementation code.

Deliverables:
- docs/documentation_research.md
- concise summary of official vs unofficial tools
- implementation recommendations
- known risks
```

---

### Agent 1 — Product Requirements Agent

```text
You are the Product Requirements Agent for HabitOS.

Your job is to define the MVP product behavior and habit model.

Do not write backend code.
Do not design database migrations.
Focus on behavior, scope, and habit definitions.

Deliverables:
- docs/product_requirements.md
- habit definitions table
- MVP acceptance criteria
- non-goals
- future expansion list
```

---

### Agent 2 — Core Domain/Data Model Agent

```text
You are the Core Domain/Data Model Agent for HabitOS.

Your job is to design the normalized data model and core domain logic.

Do not implement external API clients.
Do not build the PDF renderer.
Do not build reMarkable sync.

Deliverables:
- docs/data_model.md
- packages/core/models.py
- enum definitions
- sample JSON for one day and one month
```

---

### Agent 3 — Habit Rule Engine Agent

```text
You are the Habit Rule Engine Agent for HabitOS.

Your job is to implement deterministic pure functions that turn normalized source events into daily habit entries.

Do not call external APIs.
Do not render PDFs.
Do not sync to reMarkable.

Default rules:
- workout checked if duration >= 15 minutes
- workout partial if duration >= 5 minutes
- meditation checked if duration >= 5 minutes
- meditation partial if duration >= 2 minutes
- sleep checked if duration >= configured target
- sleep warning if sleep exists but is below target
- recovery checked/warning based on configured recovery score bands
- journaling manual only for v1
- deep work manual only for v1

Deliverables:
- packages/core/rules.py
- packages/core/config.py
- tests/core/test_rules.py
```

---

### Agent 4 — PDF Renderer and Planner UX Agent

```text
You are the PDF Renderer and Planner UX Agent for HabitOS.

Your job is to generate a beautiful monthly hyperlinked PDF for reMarkable 2 from a JSON month state.

Do not build WHOOP integration.
Do not build Muse integration.
Do not build reMarkable sync.

Use HTML/CSS templates and Playwright to generate PDF.

Deliverables:
- packages/renderer/render_month.py
- packages/renderer/templates/month.html
- packages/renderer/templates/day.html
- packages/renderer/templates/week.html
- packages/renderer/templates/summary.html
- packages/renderer/static/remarkable.css
- data/sample/sample_month.json
- data/generated/YYYY-MM-habit-dashboard.pdf
```

---

### Agent 5 — WHOOP Connector Agent

```text
You are the WHOOP Connector Agent for HabitOS.

Your job is to implement the WHOOP integration in isolation.

Do not build the PDF renderer.
Do not build the admin UI.
Do not build Muse integration.
Do not build generic habit rules except mapping WHOOP data into normalized events.

Use the latest official WHOOP Developer documentation before implementing.

Deliverables:
- packages/connectors/whoop/client.py
- packages/connectors/whoop/auth.py
- packages/connectors/whoop/webhook.py
- packages/connectors/whoop/normalizer.py
- tests/connectors/test_whoop_normalizer.py
- docs/whoop_integration.md
```

---

### Agent 6 — Meditation Ingestion Agent

```text
You are the Muse/Meditation Ingestion Agent for HabitOS.

Your job is to determine and implement the simplest reliable way to get meditation sessions into HabitOS.

Do not build WHOOP integration.
Do not build PDF rendering.
Do not build reMarkable sync.

Preferred MVP order:
1. Manual "I meditated" endpoint
2. Apple Health Mindful Minutes import if practical
3. Muse export import if available
4. Muse SDK later

Deliverables:
- docs/meditation_ingestion.md
- packages/connectors/meditation/manual.py
- optional packages/connectors/meditation/apple_health_import.py
- optional packages/connectors/meditation/muse_import.py
- tests/connectors/test_meditation_normalizer.py
```

---

### Agent 7 — reMarkable 2 Sync Agent

```text
You are the reMarkable 2 Sync Agent for HabitOS.

Your job is to design and implement safe ways to get generated PDFs onto a reMarkable 2.

Do not build PDF rendering.
Do not build WHOOP/Muse integration.
Do not directly modify handwritten notebook internals in v1.

Deliverables:
- packages/remarkable_sync/base.py
- packages/remarkable_sync/manual.py
- optional packages/remarkable_sync/rmcl_sync.py
- optional packages/remarkable_sync/usb_web.py
- docs/remarkable_sync.md
```

---

### Agent 8 — Backend API and Scheduler Agent

```text
You are the Backend API and Scheduler Agent for HabitOS.

Your job is to create the FastAPI app that orchestrates source events, habit evaluation, PDF rendering, and sync jobs.

Do not implement WHOOP internals beyond calling the WHOOP connector interface.
Do not design the PDF layout.
Do not implement reMarkable sync internals beyond calling the sync interface.

Persistence: MongoDB via PyMongo Async — use the existing repositories in
`packages/core/repositories/`. Do not introduce SQLAlchemy, Alembic, or
Postgres. Wire `ensure_indexes()` into the FastAPI lifespan handler.

Deliverables:
- apps/api/main.py
- apps/api/routes/
- apps/api/services/
- apps/api/scheduler.py
- apps/api/lifespan.py (Mongo client + ensure_indexes on startup)
- .env.example updates if new vars are needed
- README.md updates
```

---

### Agent 9 — Admin/Debug UI Agent

```text
You are the Admin UI Agent for HabitOS.

Your job is to build a small debugging dashboard, not a new daily habit app.

Use:
- Next.js 15
- TypeScript
- Tailwind
- shadcn/ui

Deliverables:
- apps/admin/
- event inspection page
- daily habit state page
- render/sync page
- settings page
```

---

### Agent 10 — Security, Privacy, and Reliability Agent

```text
You are the Security, Privacy, and Reliability Agent for HabitOS.

Your job is to review the architecture for privacy, token safety, health data handling, and operational reliability.

Deliverables:
- docs/security_privacy.md
- .env.example review
- token encryption plan
- webhook security checklist
- reliability checklist
```

---

### Agent 11 — Integration Agent

```text
You are the Integration Agent for HabitOS.

Your job is to assemble the isolated components into a working MVP without expanding scope.

Target MVP:
fake/sample data → normalized month state → hyperlinked PDF → manual upload instructions

Then:
WHOOP data → normalized events → habit entries → regenerated PDF

Deliverables:
- working MVP branch
- root README.md
- Makefile commands
- final architecture diagram
- known limitations
```

---

## 9. Execution order

```text
1. Agent 0 — Documentation research
2. Agent 1 — Product requirements
3. Agent 2 — Data model
4. Agent 4 — PDF renderer with fake JSON
5. Agent 3 — Rule engine
6. Agent 8 — Backend API/scheduler
7. Agent 5 — WHOOP connector
8. Agent 7 — reMarkable sync
9. Agent 6 — Muse/meditation ingestion
10. Agent 9 — Admin/debug UI
11. Agent 10 — Security/reliability review
12. Agent 11 — Integration/merge
```

If time is limited, stop after Agent 4 and manually upload the generated PDF. That is already a useful first artifact.

---

## 10. Definition of done for MVP

The MVP is done when:

```text
make render-current-month
```

produces a readable, hyperlinked monthly PDF that can be uploaded to reMarkable 2 and used for one week.

Everything else is secondary.
