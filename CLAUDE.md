# CLAUDE.md

@AGENTS.md
This file gives Claude Code and other coding agents project-specific instructions for **HabitOS**.

HabitOS is a small local-first automation system that converts tracker data into a beautiful monthly habit dashboard for **reMarkable 2**.

Read this file before making changes.

---

## 1. Mission

Build the smallest useful version of HabitOS:

```text
sample data
  → normalized habit month state
  → hyperlinked monthly PDF
  → manual upload to reMarkable 2
```

Then expand carefully:

```text
WHOOP
  → normalized source_events
  → habit_entries
  → regenerated PDF
  → optional reMarkable sync
```

The user wants a tiny improvement to their existing workflow, not another productivity platform.

---

## 2. Product principles

Follow these strictly:

1. **Small before impressive**
2. **Useful before automated**
3. **The PDF experience comes before API integrations**
4. **The backend/database is the source of truth**
5. **The reMarkable PDF is a generated artifact**
6. **Do not overwrite handwritten notebooks**
7. **No shame-based streak design**
8. **No raw EEG/Muse complexity in the MVP**
9. **No native reMarkable app in the MVP**
10. **No unnecessary infrastructure**

A good first version is a beautiful generated PDF from fake JSON.

---

## 3. User/device context

The user has a **reMarkable 2**.

Do not assume reMarkable Paper Pro Developer Mode instructions apply.

For reMarkable 2 sync, prefer this order:

1. Manual PDF upload
2. USB web interface if available
3. reMarkable Cloud community tools such as `rmcl` or `rmapi`
4. SSH/local sync only later and only behind an adapter

Generated dashboards are machine-owned files. Human handwritten notebooks are not to be overwritten.

---

## 4. Preferred architecture

```text
Trackers / APIs / manual imports
  → connectors
  → normalized source_events
  → habit rule engine
  → habit_entries
  → generated monthly PDF
  → reMarkable sync adapter
```

Recommended repo structure:

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
    admin/

  packages/
    core/
    connectors/
    renderer/
    remarkable_sync/

  data/
    sample/
    generated/

  tests/
  docs/
```

---

## 5. Technology choices

Use boring tools.

### Backend

Use:

```text
FastAPI
Pydantic
PyMongo Async (pymongo >= 4.9, AsyncMongoClient)
MongoDB (local or Atlas)
APScheduler first
```

Do not use SQLAlchemy, Alembic, Postgres, Redis, Celery, Kubernetes, or
Docker for a database. Repositories under `packages/core/repositories/` are
the only layer allowed to touch MongoDB; everything else stays storage-
agnostic. Motor is not used — PyMongo's native async client is the
supported direction.

See `docs/persistence.md` for collection design and indexes.

### PDF renderer

Use:

```text
HTML/CSS templates
Playwright print-to-PDF
```

Optimize for:

- grayscale
- high contrast
- large tap targets
- readable text on reMarkable 2
- internal links
- handwriting space

### Admin UI

Optional only. If created, use:

```text
Next.js 15
TypeScript
Tailwind
shadcn/ui
```

The admin UI is for debugging, not daily habit tracking.

---

## 6. Current external documentation

Before implementing service-specific code, check the latest documentation.

### WHOOP

- API reference: https://developer.whoop.com/api/
- Webhooks: https://developer.whoop.com/docs/developing/webhooks/

Current assumptions:

- OAuth 2.0 authorization code flow.
- Useful scopes:
  - `read:workout`
  - `read:sleep`
  - `read:recovery`
  - `read:cycles`
  - `read:profile`
- Webhooks should be treated as notifications.
- Fetch full resources after webhook receipt.
- Reconciliation is required because events can be duplicated, delayed, or missed.

### Muse

- SDK: https://choosemuse.com/pages/developers
- Apple Health integration support: https://choosemuse.my.site.com/s/article/Integrating-Muse-with-Apple-Health

Current assumptions:

- Do not start with raw Muse SDK or EEG data.
- Prefer manual endpoint or Apple Health Mindful Minutes import first.
- Muse SDK may be useful later but is not an MVP dependency.

### reMarkable

- Official developer docs: https://developer.remarkable.com/documentation
- USB web interface guide: https://remarkable.guide/tech/usb-web-interface.html
- SSH guide: https://remarkable.guide/guide/access/ssh.html
- rmcl: https://github.com/rschroll/rmcl
- rmapi: https://github.com/juruen/rmapi
- rmapy: https://github.com/subutux/rmapy
- ReCalendar inspiration: https://github.com/klimeryk/recalendar.js

Current assumptions:

- Manual upload first.
- Cloud or USB automation later.
- Do not directly modify internal notebook files in v1.

---

## 7. Core domain language

Use these names consistently.

### Event types

```text
workout
sleep
recovery
meditation
deep_work
journal
manual
```

### Sources

```text
whoop
muse
apple_health
manual
calendar
github
remarkable
```

### Habit statuses

```text
checked
partial
warning
missed
manual
```

### Initial habit keys

```text
workout
sleep
recovery
meditation
journaling
deep_work
```

---

## 8. Initial rules

Implement rules as deterministic pure functions.

Default thresholds:

```text
workout:
- checked if duration >= 15 minutes
- partial if duration >= 5 minutes
- missed if no qualifying event

meditation:
- checked if duration >= 5 minutes
- partial if duration >= 2 minutes
- missed if no qualifying event

sleep:
- checked if duration >= configured target
- warning if sleep exists but is below target
- missed if no sleep data

recovery:
- checked/warning based on configured score bands

journaling:
- manual only for v1

deep_work:
- manual only for v1
```

Manual overrides take priority over automatic detection.

Every habit entry should include:

```text
status
summary
description
source
confidence
linked_source_event_ids
explanation
```

---

## 9. Coding rules

### General

- Keep modules small.
- Prefer explicit functions over hidden framework magic.
- Write testable pure functions for core logic.
- Avoid unnecessary dependencies.
- Do not create generic abstractions before there are two real implementations.
- Do not hide errors silently.
- Add clear README notes for commands.

### Python

- Use type hints.
- Use Pydantic models for boundary data.
- Keep external API payloads isolated in connector modules.
- Normalize external data before core rules see it.
- Store timestamps in UTC plus computed local date.

### Frontend/admin

- Keep UI minimal.
- Do not build a full habit app.
- The admin UI should inspect, override, render, and sync.
- Daily user experience should remain on reMarkable.

### PDF

- No color-dependent meaning.
- Use e-ink-friendly contrast.
- Avoid tiny fonts.
- Keep link targets large.
- Include back links from daily pages to monthly dashboard.
- Add blank writing space.

---

## 10. Important safety/privacy rules

HabitOS handles health and behavior data.

- Never commit `.env`.
- Never commit OAuth tokens.
- Never commit real raw health payloads.
- Never commit generated PDFs containing private data unless explicitly intended.
- Use `.gitignore` for `data/generated/*` except `.gitkeep`.
- Add `data/sample/` fake data only.
- Token encryption should be added before serious hosted use.
- Webhooks must validate signatures if supported by the provider.
- Admin UI should not be exposed publicly without auth.

---

## 11. Initial commands to support

Eventually support:

```bash
make setup
make test
make render-sample
make render-current-month
make reconcile
make run-api
```

For the first milestone, only these are required:

```bash
make setup
make test
make render-sample
```

---

## 12. MVP acceptance criteria

The first MVP is complete when:

```bash
make render-sample
```

creates:

```text
data/generated/YYYY-MM-habit-dashboard.pdf
```

And the PDF has:

- monthly dashboard page
- daily detail pages
- internal links from month → day
- internal links from day → month
- grayscale-friendly habit states
- handwriting space
- readable layout on reMarkable 2

No real WHOOP/Muse integration is required for the first MVP.

---

## 13. What not to do

Do not:

- build a native reMarkable app
- parse or modify reMarkable notebook internals
- start with SSH-based sync
- start with raw Muse SDK/EEG
- build a social/gamified habit platform
- add a complex admin dashboard before the PDF works
- add LLM coaching before deterministic summaries work
- add SQLAlchemy/Alembic/Postgres/Redis/Celery — persistence is MongoDB-only, see `docs/persistence.md`
- make the user depend on a web dashboard for daily tracking

---

## 14. Recommended implementation order

1. Create sample month JSON.
2. Create HTML/CSS renderer.
3. Generate PDF with internal links.
4. Add core Pydantic models.
5. Add pure habit rule functions.
6. Add FastAPI orchestration.
7. Add WHOOP connector.
8. Add manual reMarkable sync adapter.
9. Add meditation import.
10. Add optional admin/debug UI.

If blocked, return to the smallest useful artifact: a generated PDF that the user can upload manually.

---

## 15. Handoff notes for agents

When completing a task, update or create:

- relevant docs in `docs/`
- relevant tests in `tests/`
- README instructions if commands changed
- sample data if behavior changed

Do not make broad unrelated changes.

Every PR/change should state:

```text
What changed
Why it changed
How to test it
What is intentionally not included
```

---

## 16. North star

The north star is not automation for its own sake.

The north star is:

> A calm reMarkable 2 dashboard that quietly reflects what the user already did, helps them notice patterns, and requires almost no extra brain power.
