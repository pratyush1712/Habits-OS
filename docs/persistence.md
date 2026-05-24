# HabitOS persistence

The persistence layer is **MongoDB** (Atlas or local). The renderer and rule
engine do not touch the database; only repositories under
`packages/core/repositories/` know about BSON, `_id`, or ObjectId. Pydantic
models in `packages/core/models.py` are the application-facing schema.

Connection settings come from environment variables; see `.env.example`.

## Why MongoDB

- Documents map cleanly onto our event/entry shapes (free-form `metrics` and
  `raw_payload` per source, no schema-evolution friction as connectors land).
- No migrations toolchain to maintain; indexes are declarative and applied
  idempotently at startup.
- Atlas removes the need to run Postgres + Docker locally for hosted use.

## Stack choices

|                  |                                                              |
| ---------------- | ------------------------------------------------------------ |
| Driver           | `pymongo>=4.9`, **async client** `pymongo.AsyncMongoClient`  |
| ID strategy      | deterministic string `_id` from natural keys where possible  |
| Date storage     | ISO string `"YYYY-MM-DD"` (sorts chronologically, indexable) |
| Datetime storage | BSON ISODate (Python `datetime`, always UTC)                 |
| Binary storage   | BSON BinData (Python `bytes`) — used for encrypted tokens    |
| Schema evolution | additive, validated by Pydantic on read                      |
| Migrations       | none; `ensure_indexes()` is the only build step              |

> Motor is **not** used. PyMongo's native async client (4.9+) is the supported
> direction; Motor is being deprecated.

## Collections

### `source_events`

Normalized events ingested from connectors or manual imports.

- `_id`: `f"{source}:{source_event_id}"` — natural key, supports idempotent
  webhook reconciliation via `replace_one(..., upsert=True)`.
- Application shape: `SourceEvent`.

Secondary indexes:

- `{local_date: 1, event_type: 1}` — rule engine's daily-event lookup
- `{start_time_utc: -1}` — recency queries
- `{source: 1, local_date: -1}` — "WHOOP events in May 2026"

### `manual_overrides`

User-asserted entries that win over computed results.

- `_id`: `f"{date}:{habit_key}"` — one override per habit per day.
- Application shape: `HabitOverride`.

Secondary indexes:

- `{date: 1}` — month-range queries

### `habit_entries`

Resolved entries produced by the rule engine. This is the source of truth for
the renderer.

- `_id`: `f"{date}:{habit_key}"` — one resolved entry per habit per day.
- Application shape: `HabitEntry`.

Secondary indexes:

- `{date: 1, status: 1}` — "show all warnings in May"
- `{ruleset_version: 1}` — selective recompute when rule thresholds change

> `MonthHabitState` is **not** persisted as a snapshot. The renderer assembles
> it via `HabitEntriesRepo.get_state(month, habits)`.

### `render_jobs`

Audit trail of PDF render requests.

- `_id`: `ObjectId` — no natural key (many renders of the same month over
  time are valid).
- Application shape: `RenderJob` (`id: str` field; ObjectId never leaks past
  the repo).

Secondary indexes:

- `{month: 1, requested_at: -1}` — latest render for a month
- `{status: 1, requested_at: -1}` — queue / failure inspection

### `automation_runs`

Audit trail of nightly, manual, and rollover automation runs.

- `_id`: `ObjectId` — many automation runs over time are valid.
- Application shape: `AutomationRun` (`id: str` field; ObjectId never leaks past
  the repo).

Secondary indexes:

- `{started_at: -1}` — newest automation runs first
- `{run_type: 1, started_at: -1}` — filter nightly vs manual vs rollover
- `{status: 1, started_at: -1}` — inspect failed runs quickly

### `source_accounts`

OAuth-connected sources (WHOOP, Muse, ...).

- `_id`: `f"{source}:{external_user_id}"`.
- Application shape: `SourceAccount`.
- `encrypted_access_token` / `encrypted_refresh_token` stored as BSON
  BinData. **Encryption is deferred** — see CLAUDE.md §10. The field type is
  reserved so a future Fernet/libsodium layer can drop in without a schema
  change.

Secondary indexes:

- `{source: 1}` — "list all WHOOP accounts"

### `habits`

The habit catalog.

- `_id`: the habit `key` (e.g. `"workout"`).
- Application shape: `Habit`.
- `archived_at: ISODate | null` is persisted alongside the model; soft-delete
  preserved across `upsert`s via `$setOnInsert`.

Secondary indexes:

- `{archived_at: 1}` — `list_active()` query (`archived_at: null`)

## Indexes module

All indexes are declared in `packages/core/indexes.py` as `IndexModel` lists
keyed by collection name. `ensure_indexes(db)` creates them idempotently and
returns the created names. Call it from the FastAPI lifespan handler when M3
lands.

> Natural-key uniqueness is provided by the `_id` index that MongoDB creates
> automatically; no redundant unique secondary indexes are declared.

## Month queries

Months use the ISO string convention so that `local_date` / `date` indexes
serve both "give me May 2026" and "give me 2026-05-14" without an extra
`month` field. Helper:

```python
from packages.core.repositories.base import month_range

start, end = month_range("2026-05")   # ("2026-05-01", "2026-06-01")
cursor = coll.find({"date": {"$gte": start, "$lt": end}})
```

## Testing

Repository tests are real-Mongo integration tests. They are **skipped
automatically** when `MONGODB_TEST_URI` is unset, so the suite is green for
contributors without a local Mongo. To run them:

```bash
export MONGODB_TEST_URI=mongodb://localhost:27017
make test
```

Each test gets its own uniquely-named database (`habitos_test_<hex>`), dropped
on teardown — no state leaks between tests, and the production database is
never touched.

Pure-logic helpers (BSON ↔ Pydantic conversion, month-range math) are tested
in `tests/core/test_repo_base.py` without Mongo.

## Encryption-at-rest (deferred)

Per CLAUDE.md §10, token encryption is required before hosted use. The
intended shape:

1. A `packages/core/crypto.py` module wraps Fernet (symmetric, key from env).
2. `SourceAccount.encrypted_access_token` / `encrypted_refresh_token` are
   already typed as `bytes`, so no schema change.
3. A service-layer wrapper above `SourceAccountsRepo` calls `encrypt(token)`
   on the way in and `decrypt(blob)` on the way out — the repo itself stays
   storage-agnostic.

For local development against a non-hosted Mongo, leaving tokens unencrypted
is fine. Production deployment must not skip this step.
