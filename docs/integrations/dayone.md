# HabitOS Integration: Day One

## 1. Service name

Day One (Automattic) — macOS journaling app, local SQLite database.

## 2. Desired HabitOS use case

Answer one question on the monthly reMarkable dashboard: **did I journal
on this date?** Optionally surface how many entries were created. The
integration feeds the `journaling` habit (rule: `>=1` entry that day ⇒
`checked`). Full entry text is intentionally never read.

## 3. Official documentation links

- API reference: **None.** Day One has no public REST/HTTP API. Only the
  official MCP server, the `dayone2` CLI (macOS, primarily write-oriented),
  URL schemes, and manual JSON export are available.
- Auth / OAuth docs: N/A — local file access only for MVP.
- Webhook docs: N/A — no public webhooks.
- Rate-limit docs: N/A — local SQLite reads.
- Export/import docs: in-app JSON+media zip export. Out of scope for MVP.

## 4. Unofficial / community documentation links

- [`kwo/dayone2md`](https://github.com/kwo/dayone2md) — reads the modern
  Day One SQLite schema. Used only as a reference for column/pivot names;
  no code is imported. The tool's purpose (full markdown export) is the
  opposite of our metadata-only stance.
- [`nathangrigg/dayone_export`](https://github.com/nathangrigg/dayone_export)
  — reads legacy export files; not relevant to live DB access.

## 5. Integration feasibility decision

**Build now.** Local SQLite is available, headless, free of OAuth, and
can be read in a metadata-only way that satisfies the privacy goal by
construction.

## 6. Integration type

**Local file/export import** (read-only access to the macOS app's SQLite
database). MCP server is the documented fallback path and is **not
implemented** in this MVP.

## 7. Authentication model

- Type: `AuthType.LOCAL_FILE`
- Scopes: N/A
- Token lifetime: N/A
- Refresh flow: N/A
- Token storage: N/A
- Required env vars: `DAYONE_DB_PATH`
- macOS may require granting Full Disk Access to the process running
  HabitOS so `sqlite3` can read the Day One Group Container.

## 8. Account identity model

- External user identifier field: not used. Day One is a single-user
  local app for the purposes of HabitOS.
- Display name field: N/A
- Multi-account support: no.
- `external_user_id`: N/A (no `SourceAccount` row needed).

## 9. Available data

Read per entry (metadata only by default):

- `ZENTRY.ZUUID` — entry UUID
- `ZENTRY.ZCREATIONDATE` — Core Data epoch seconds (offset `+978_307_200`
  to convert to Unix epoch)
- `ZENTRY.ZGREGORIANYEAR` / `ZGREGORIANMONTH` / `ZGREGORIANDAY` — used as
  the entry's local date (Day One stores these alongside the timestamp so
  we never need to interpret the `ZTIMEZONE` BLOB).
- `ZJOURNAL.ZNAME`, `ZJOURNAL.ZUUIDFORAUXILIARYSYNC` — journal name and id
- Tags via the runtime-resolved pivot table (e.g. `Z_8TAGS`, `Z_17TAGS`).
  Optional and best-effort: if the pivot cannot be resolved confidently,
  `metrics.tags` is omitted entirely (we never assert "no tags" when we
  don't actually know).

Opt-in only via `DAYONE_INCLUDE_TEXT=true`:

- Word count derived from `LENGTH(ZMARKDOWNTEXT)`. The text itself is
  still **never** persisted.

## 10. Missing / unavailable data

- `ZTIMEZONE` is a BLOB in current schemas; we don't parse it.
- Photos, audio, location, weather, and rich-text blocks are out of scope.
- No way to detect "entry started but not saved" from the DB alone.

## 11. Rate limits

N/A — local file reads.

## 12. Pagination

Single SQL `SELECT` over the requested date window; no pagination needed.

## 13. Webhook support

Not supported (no API).

## 14. Export / import support

Not used. Manual JSON export remains available for one-off backfill or
debugging but is not part of the nightly path.

## 15. Privacy / security concerns

- Entry text is **never** read or persisted in the default mode.
- Even with `DAYONE_INCLUDE_TEXT=true`, only the derived word count is
  stored in `metrics.total_word_count`. The text itself never enters
  `raw_payload`; an allowlist in `normalizer.py` enforces this.
- Journal names and tag names are stored in `metrics`. They can be
  sensitive ("Therapy", etc.); `DAYONE_JOURNAL_FILTER` lets the user
  restrict which journals are read.
- `/automation/status` does **not** expose journal names, tag names, or
  entry UUIDs from the Day One summary — only counts, inserted/updated,
  affected months, `skipped_reason`, and warnings.
- The DB is snapshotted to a temporary directory before reading and the
  directory is removed in a `finally` block so no Day One bytes are left
  on disk.
- The snapshot is opened with the URI `mode=ro&immutable=1`; the live DB
  is never modified.
- Hidden, trash, and draft entries are filtered out at the SQL level.

## 16. Required env vars

```text
DAYONE_SYNC_MODE        # only "sqlite" is implemented
DAYONE_DB_PATH          # leave empty to disable
DAYONE_INCLUDE_TEXT     # default false
DAYONE_LOOKBACK_DAYS    # default 3
DAYONE_JOURNAL_FILTER   # optional CSV
DAYONE_TIMEZONE         # fallback IANA name; default UTC
```

All of these are added to `.env.example`.

## 17. Data mapping to `SourceEvent`

One `SourceEvent` per `(source="day_one", local_date)`.

| External field | `SourceEvent` field | Notes |
|---|---|---|
| `dayone:{local_date.isoformat()}` | `source_event_id` | Daily aggregate key, stable across reruns |
| n/a | `source` | Always `"day_one"` |
| n/a | `event_type` | Always `"journal"` |
| min(`ZENTRY.ZCREATIONDATE`) for that day | `start_time_utc` | UTC of first entry of the day |
| max(`ZENTRY.ZCREATIONDATE`) for that day | `end_time_utc` | UTC of last entry of the day (equal to start for single-entry days) |
| `ZENTRY.ZGREGORIANYEAR/MONTH/DAY` | `local_date` | Day One's own gregorian fields; falls back to UTC date when absent |
| n/a | `timezone` | `DAYONE_TIMEZONE` (default `"UTC"`) — label only |
| n/a | `title` | `"N journal entr(y/ies)"` |
| n/a | `description` | `""` (intentionally empty — no text leakage) |
| count(*) | `metrics.entry_count` | int |
| set(`ZJOURNAL.ZNAME`) | `metrics.journal_names` | sorted, deduped |
| set(`ZJOURNAL.ZUUIDFORAUXILIARYSYNC`) | `metrics.journal_ids` | sorted, deduped |
| union of tags | `metrics.tags` | omitted when pivot is unresolved |
| sum(word_count) when opted-in | `metrics.total_word_count` | absent otherwise |
| list of `ZENTRY.ZUUID` | `raw_payload.entry_uuids` | only structural metadata in raw_payload |
| snapshot timestamp | `raw_payload.snapshot_taken_at` | ISO UTC |
| `Z_METADATA.Z_VERSION` | `raw_payload.db_schema_version` | may be `null` |
| `"dayone_sqlite"` | `raw_payload.source_kind` | which reader produced this |

The `raw_payload` allowlist is enforced in `normalizer.py` via
`RAW_PAYLOAD_ALLOWED_KEYS`; an assertion fires if a contributor adds a key
outside the allowlist.

## 18. Habit mappings

| Habit key | Driven by event_type | Rule notes |
|---|---|---|
| `journaling` | `journal` | `evaluate_journaling`: any entry that day ⇒ `checked`. Threshold lives on `HabitRuleConfig.journaling.checked_min_entries` (default 1). |

## 19. Default habits needed

The existing `journaling` habit was flipped from `kind="manual"` to
`kind="auto"` with sources `["day_one", "manual"]`. No new habit was
created.

## 20. Rule engine changes needed

- New evaluator `evaluate_journaling` in `packages/core/rules.py`.
- New `JournalingRule(checked_min_entries=1)` on `HabitRuleConfig`.
- Tests in `tests/core/test_rules_journaling.py`.

## 21. Backfill behavior

- Supported: yes (any historical window the local DB still holds).
- Maximum historical window: bounded only by the Day One DB itself.
- Cost of a full backfill: single SQL query over a date range; cheap.

## 22. Reconciliation behavior

- Service revises historical records? Yes — Day One sync can backdate
  edits and entries.
- Recommended reconcile window: 3 days (`DAYONE_LOOKBACK_DAYS=3`).
- Idempotency key: `(source, source_event_id)` ⇒ `("day_one", "dayone:YYYY-MM-DD")`.

## 23. Automation compatibility

```python
ConnectorCapability(
    nightly_eligible=True,
    supports_date_range_sync=True,
    supports_backfill=True,
    supports_reconciliation=True,
    recommended_reconcile_window_days=3,
    service_revises_historical_data=True,
    sync_is_idempotent=True,
    required_env_vars=["DAYONE_DB_PATH"],
    graceful_when_unconfigured=True,
)
```

## 24. Error handling

- **Skipped (no error, summary returned):**
  - `DAYONE_SYNC_MODE != "sqlite"` ⇒ `skipped_reason="unsupported_sync_mode"`
  - `DAYONE_DB_PATH` unset ⇒ `skipped_reason="missing_db_path"`
  - DB file missing ⇒ `skipped_reason="dayone_db_unavailable"`
  - DB file present but unreadable (`DayOneReadError`) ⇒
    `skipped_reason="dayone_db_unreadable"`
  - Schema mismatch (`DayOneSchemaError`) ⇒
    `skipped_reason="dayone_schema_unsupported"`
- **Raised:** only `end < start` (input validation; the route maps this to
  HTTP 400, and `AutomationService` never passes inverted ranges).
- The nightly pipeline never re-raises Day One failures — they always show
  up as a skipped summary in `automation_runs.dayone_summary`.

## 25. API routes

- `GET /dayone/status` — configured / `db_exists` / mode / `include_text` /
  `lookback_days` / `journal_filter`.
- `POST /dayone/sync?start=YYYY-MM-DD&end=YYYY-MM-DD&recompute=true` — sync
  a manual date range and (optionally) recompute affected months.

## 26. Tests

- `tests/core/test_models.py` — covers the new `"day_one"` literal and the
  `dayone_summary` field on `AutomationRun`.
- `tests/connectors/test_dayone_normalizer.py` — single/multi-entry days,
  raw_payload allowlist enforcement, tags-known vs tags-unknown behavior,
  no text under default settings.
- `tests/connectors/test_dayone_sqlite_reader.py` — builds a minimal
  Day One-shaped SQLite fixture; resolves the tag pivot at runtime; rejects
  databases missing `ZENTRY`/`ZJOURNAL`; honors `journal_filter`.
- `tests/api/test_dayone_sync_service.py` — covers each `skipped_reason`
  path and the idempotency invariant (`inserted == 0` on second run).
- `tests/core/test_rules.py` — adds journaling cases.
- `tests/api/test_automation_service.py` — verifies the Day One summary
  flows through `complete()` and that affected months are unioned.

## 27. Docs to update

- [x] `docs/integrations/dayone.md` (this file)
- [x] `.env.example`
- [x] `docs/automation.md` (added to the nightly pipeline)
- [ ] `README.md` — no new user-facing command beyond the existing
  automation endpoints, so no update.

## 28. MVP recommendation

The smallest reliable Day One integration: HabitOS quietly reads the
local Day One SQLite each nightly run, counts entries per day, writes
one `SourceEvent` per local date, and the journaling habit lights up on
the monthly PDF whenever at least one entry exists. No text leaves
Day One. No OAuth. No new daemon. Disabling is a one-line env change.

## 29. Decision

**Build now** — implemented metadata-only via local SQLite. MCP server
remains the documented fallback if schema drift breaks the SQLite reader
in a future Day One release. Day One writeback is explicitly out of scope.
