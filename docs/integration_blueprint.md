# HabitOS Integration Blueprint

_Last updated: 2026-05-24_

This document defines how new integrations are added to HabitOS. It is the
authoritative reference. Every future connector — Muse, Day One, Apple
Health, a smart medication tool, a new wearable — must conform to this
blueprint before merging.

If something here conflicts with what the WHOOP connector currently does,
WHOOP is the legacy reference: it predates this contract. The migration
path is documented in §Integration Registry — Future Migration.

---

## 1. Integration philosophy

HabitOS is a small, local-first system. It exists to make the user's
existing behavior visible on a calm reMarkable 2 dashboard with as little
maintenance burden as possible.

Three rules govern every integration:

1. **Calm before clever.** A reliable manual import beats a fragile API
   integration. If a service does not expose a usable API, a manual
   endpoint, file import, or Apple Health bridge is a legitimate MVP.
2. **Normalize first, decide later.** Connectors translate external data
   into `SourceEvent` records. They do not decide what counts as a habit.
3. **Reversible by default.** Every integration must be safe to disable,
   safe to rerun, and safe to fail. Nightly automation must not require
   any specific integration to be enabled.

---

## 2. Source of truth model

```text
External service
  → connector (HTTP / file / webhook / manual)
  → normalize() → SourceEvent
  → SourceEventsRepo (MongoDB)
  → habit rule engine (pure)
  → HabitEntry
  → MonthHabitState (derived)
  → PDF renderer
  → reMarkable lifecycle
```

The integration boundary is **`SourceEvent`**. Everything above the line
is connector-owned. Everything below the line is HabitOS core, and must
not know which service produced an event.

### Why integrations must normalize into `SourceEvent`

- The rule engine is pure and source-agnostic. It groups events by
  `local_date` and `event_type` and applies thresholds. Letting connectors
  inject service-specific shapes would couple rules to vendors.
- `SourceEvent` carries `raw_payload` for audit/debug. Connectors should
  copy stable, rule-relevant fields into `metrics` and leave the rest in
  `raw_payload`.
- Dedupe is `source` + `source_event_id`. New integrations get safe
  upsert behavior for free.

### Why integrations must NOT write `habit_entries`

`habit_entries` are derived state, not input state. They are produced by:

1. The deterministic rule engine in `packages/core/rules.py`, given
   `SourceEvent`s and rule config, or
2. The manual override system (`ManualOverridesRepo`), which the user
   asserts directly.

A connector that writes `habit_entries` would:

- bypass the rule engine, so reconciliation no longer corrects history;
- bypass manual overrides, so the user's authority is overruled;
- create source-specific habit semantics that the renderer cannot rely on.

The only acceptable shortcut is a manual endpoint that writes a
`HabitOverride`, which the rule engine then respects.

---

## 3. How a new integration fits into the pipeline

| HabitOS surface | What the integration must do |
|---|---|
| `source_events` collection | Normalize raw records into `SourceEvent`; upsert via `SourceEventsRepo`. Use `source` + `source_event_id` for idempotency. |
| `source_accounts` collection | If OAuth/API-key, store credentials via `SourceAccountsRepo`. Tokens stored as `bytes` to allow future encryption. |
| Rule engine (`packages/core/rules.py`) | Either rely on an existing per-habit evaluator, or contribute a new pure rule. New rules must not call the connector. |
| `habit_entries` collection | Written by `HabitEvaluationService.recompute(month)`. Connectors must never write here. |
| `MonthHabitState` | Derived on read from `habit_entries` + `habits`. No connector action needed. |
| PDF renderer | No connector action needed. New event types may need new descriptions in `metrics`, but rendering is centralized. |
| `automation_runs` collection | Connector summaries flow up to `AutomationService`. Today this is a named field per integration; tomorrow it is a generic dict (see §10). |
| Nightly automation | Connectors that participate expose `sync_range()` and declare capabilities; see §Automation Compatibility Contract. |
| reMarkable lifecycle | No connector action. Lifecycle is centralized in `RemarkableLifecycleService`. |

---

## 4. Integration types

There is no single right shape. Pick the smallest reliable path for the
service.

| Type | When to use | Example |
|---|---|---|
| **OAuth pull API** | Service has an official OAuth API with date-range endpoints | WHOOP |
| **API-key pull API** | Service has a simple API-key authenticated REST API | hypothetical wearable |
| **Webhook push API** | Service pushes notifications; backfill still requires pull | WHOOP webhooks (notification only — full record still pulled) |
| **Local file/export import** | Service exports JSON/CSV the user uploads manually | Day One export, Muse session export |
| **iOS Shortcut bridge** | Service is iOS-only and user can wire a Shortcut to POST data | meditation timer, journaling apps |
| **Apple Health bridge** | Service writes to Apple Health and user exports/forwards from there | Muse Mindful Minutes |
| **Manual endpoint** | No API, no export — user POSTs "I did X today" | meditation, deep work, journaling |
| **Unsupported / no viable API** | Service does not expose data and there is no bridge | document the decision in `docs/integrations/<service>.md` and stop. Do not invent a scraping path. |

### Manual-first integration as a first-class MVP pattern

Some services do not have clean APIs. That is fine. HabitOS treats the
following as legitimate first-class integration MVPs:

- A `POST /events/<source>` endpoint that lets the user assert "I
  meditated for 12 minutes today".
- A file-import endpoint that accepts a vendor export and writes
  `SourceEvent`s.
- An iOS Shortcut that POSTs to a HabitOS endpoint when a session ends.
- An Apple Health bridge that turns Mindful Minutes or workout records
  into HabitOS events.

**Future agents must not force an OAuth or API integration when the
service does not support one cleanly.** A manual-first integration that
works for one month is a real shipped integration; an OAuth integration
that needs constant credential repair is not.

Concrete services where manual-first is likely the right MVP:

- **Muse** — historical session data via Apple Health is more reliable
  than the SDK.
- **Day One** — no official API; export/import or Shortcut first.
- **Apple Health** — direct backend pull is not possible; an iOS-side
  bridge is the only practical path.
- **Smart medication tools** — evaluate the vendor's actual API before
  assuming one exists; many do not.

A manual-first integration may still graduate to a pull API later. The
`SourceEvent` shape stays identical; only the producer changes.

---

## 5. Integration feasibility checklist

Before writing code:

- [ ] Does the service expose an official API? Link the docs.
- [ ] If yes: auth model? rate limits? pagination? backfill support?
- [ ] If no: is there a usable export, Shortcut, or Apple Health path?
- [ ] What `EventType` values does the service produce?
- [ ] Do those `EventType` values already exist in
      `packages/core/models.py::EventType`? If not, the model must be
      extended (see §11).
- [ ] Is the `EventSource` literal already present? If not, the model
      must be extended.
- [ ] What habit(s) consume this data? Are the rules already in place?
- [ ] Can sync be rerun safely? What is the idempotency key?
- [ ] Should this integration participate in nightly automation? (See
      §Automation Compatibility Contract.)
- [ ] What env vars are required? Can the integration skip cleanly when
      they are unset?
- [ ] If the answer to most of these is "I don't know yet," produce a
      feasibility report first; do not start coding.

---

## 6. Documentation research checklist

For every integration:

- [ ] Linked the latest official API docs.
- [ ] Captured auth flow (OAuth scopes, key locations, token lifetime).
- [ ] Captured rate limits and pagination.
- [ ] Captured webhook support and signature verification rules.
- [ ] Captured export/import formats if relevant.
- [ ] Noted any known unreliability of third-party libraries (e.g.
      community reMarkable Cloud libraries are unofficial).

---

## 7. Authentication / security checklist

- [ ] Secrets are never committed. Env vars only.
- [ ] OAuth tokens go through `SourceAccountsRepo` as `bytes`.
- [ ] Webhook signatures are verified before any side effects.
- [ ] Connector does not log raw tokens or full identifying payloads in
      production paths.
- [ ] If the service supports scope minimization, request only what is
      needed for the habit mapping.
- [ ] `required_env_vars` is declared on the connector's
      `ConnectorCapability` and documented in `.env.example`.

---

## 8. Data mapping checklist

For each external record type → `SourceEvent`:

- [ ] `source` is set to the matching `EventSource` literal.
- [ ] `source_event_id` is stable across reruns. If the service does not
      provide one, derive it from a stable composite (e.g. service id +
      record kind) and document the choice in the connector doc.
- [ ] `event_type` matches one of the `EventType` literals.
- [ ] `start_time_utc` and `end_time_utc` are real UTC datetimes.
- [ ] `local_date` is computed at ingestion using the event's local
      timezone offset, not the server's.
- [ ] `metrics` carries only stable, rule-relevant numbers/strings.
- [ ] `raw_payload` carries the full service record for audit.
- [ ] `title` and `description` are short and renderer-friendly.

---

## 9. Idempotency, backfill, and reconciliation

### Idempotency

Every connector's write path must be safe to rerun:

- Upsert by (`source`, `source_event_id`).
- Never write a partial `SourceEvent` and then update it from a different
  path. Treat normalization as atomic.
- If the connector cannot produce a stable `source_event_id`, the
  integration is not yet ready.

### Backfill

- Backfill is `sync_range(account_id, start, end)` over an arbitrary
  historical window.
- Connectors that cannot backfill (e.g. webhook-only, no historical API)
  must declare `supports_backfill=False` on their capabilities.

### Reconciliation

- Nightly reconciliation pulls `today - HABITOS_RECONCILE_DAYS` through
  `today`. Recommended default: 14 days, matching WHOOP.
- Services that revise historical data (WHOOP often updates recovery
  after the sleep night ends) must declare
  `service_revises_historical_data=True`.
- Reconciliation must not write `habit_entries`. It writes
  `SourceEvent`s; `HabitEvaluationService.recompute(month)` then catches
  up the affected months.

### Affected months

`affected_months` in the sync summary is the sorted set of
`event.local_date.strftime("%Y-%m")` across all events written or
updated in this run. `AutomationService` uses this to know which months
to recompute.

---

## 10. Automation Compatibility Contract

Every integration that participates in nightly automation must commit to
these behaviors and surface these decisions. This section is the
contract — anything that fails it must not be wired into
`AutomationService`.

### Decisions every integration must make

| Question | Required field on `ConnectorCapability` |
|---|---|
| Is this integration eligible for nightly sync? | `nightly_eligible: bool` |
| Does it support manual date-range sync? | `supports_date_range_sync: bool` |
| Does it support backfill? | `supports_backfill: bool` |
| Does it support reconciliation of recent days? | `supports_reconciliation: bool` |
| What is the recommended reconcile window? | `recommended_reconcile_window_days: int` |
| Does the service revise historical data after initial sync? | `service_revises_historical_data: bool` |
| Can sync be safely rerun without duplicates? | `sync_is_idempotent: bool` |
| What env vars are required? | `required_env_vars: list[str]` |
| Does it skip cleanly when unconfigured? | `graceful_when_unconfigured: bool` |

### How affected months are computed

`affected_months` = `sorted({event.local_date.strftime("%Y-%m") for event in events})`
across all events written/updated by this `sync_range` call.

### What `sync_range` must return

Every automated integration exposes:

```python
async def sync_range(
    *,
    account_id: str,
    start: date,
    end: date,
    recompute: bool = False,
) -> IntegrationSyncSummary
```

`IntegrationSyncSummary` (see `packages/connectors/base.py`) carries:

- `source`
- `account_id`
- `start`, `end`
- `event_counts_by_type`
- `inserted`, `updated`
- `affected_months`
- `errors`, `warnings`
- `skipped_reason` (set when disabled/unconfigured, instead of raising)
- `extra` (connector-specific fields; do not put habit decisions here)

### Errors surfaced vs swallowed

- **Surface (raise or add to `errors`):** missing credentials when the
  integration is enabled; unexpected 5xx after retries; payload that
  fails normalization.
- **Swallow (add to `warnings`):** rate-limit backoff; expected gaps in
  data; transient timeouts that retry successfully.

A nightly run fails if any required integration raises. A nightly run
records warnings without failing.

### What appears in `/automation/status`

For each integration:

- enabled / disabled
- last successful sync
- last error (if any)
- token state (if OAuth)
- whether `required_env_vars` are present

This is read-only and safe to expose without auth on a local network;
it must not include raw tokens.

### What happens when credentials are missing

If an integration is enabled in config but credentials are missing,
`sync_range` should:

1. Set `skipped_reason="missing_credentials"` on the summary, and
2. Return rather than raise — unless the integration is _required_ by
   the current run (e.g. an explicit "sync WHOOP now" call). Required-on
   the nightly path is configured at `AutomationService`, not inside the
   connector.

This keeps the nightly run resilient when only one of N integrations is
configured.

---

## 11. Adding a new `EventSource` or `EventType`

`EventSource` and `EventType` are `Literal` unions in
`packages/core/models.py`. They are intentionally finite. Adding a new
integration may require extending one of them.

Procedure:

1. Decide whether the new source/type is genuinely new or whether an
   existing literal already covers it. (e.g. a new meditation app should
   reuse `EventType="meditation"`, not invent `"muse_meditation"`.)
2. Add the literal to `packages/core/models.py`.
3. Update `tests/core/test_models.py` to cover the new value.
4. Update any per-type renderer copy if the new event type needs
   distinct dashboard text.
5. Update `default_habits.py` if a new habit should default-on.

---

## 12. Habit mapping strategy

For each integration, decide:

- Which habit keys does this integration's data feed?
- Are those habits already in `packages/core/default_habits.py`?
- Is the rule already in `packages/core/rules.py`, or does it need a new
  pure evaluator?
- For new evaluators: write them as pure functions, no I/O, with unit
  tests in `tests/core/test_rules.py`.
- Manual overrides always win. A connector mapping must never assume its
  data is the last word on a day's status.

---

## 13. Tests required for every integration

Minimum bar:

- `tests/connectors/test_<service>_normalizer.py` — pure normalization
  cases, including missing fields, unusual timezones, and one full
  fixture per record type. No mocking required.
- `tests/connectors/test_<service>_<other>.py` — auth/client/webhook
  tests as applicable, with HTTP mocked via `respx` or `httpx`'s mock
  transport.
- `tests/api/test_<service>_sync_service.py` — service-layer test that
  exercises `sync_range` end-to-end against in-memory or test-Mongo
  repositories. Must assert idempotency by running the same range twice.
- If the integration adds a rule: `tests/core/test_rules.py` coverage
  for the new evaluator.

---

## 14. Docs required for every integration

- `docs/integrations/<service>.md` — written from the template in
  `docs/integration_template.md`.
- `.env.example` updated with any new variables.
- `docs/automation.md` updated if the integration is added to the
  nightly pipeline.
- `README.md` updated only if a new user-facing command appears.

---

## 15. When to say "this integration is not worth building"

Decline (and document the decline) when:

- The service has no API, no export, no Shortcut, and no Apple Health
  bridge. There is no path to a `SourceEvent`.
- The only available path requires reverse-engineering an unofficial
  endpoint that is likely to break.
- The data is too noisy to map to a habit (e.g. raw EEG without
  pre-processing — see CLAUDE.md §13).
- The integration would require maintaining a hosted service the user
  does not want to run.
- Manual entry is just as fast as the proposed automation (e.g. once a
  week journaling).

A documented "we considered this and decided no" is a valid deliverable.

---

## 16. Integration Registry — Future Migration

### Current state

`AutomationService.__init__` takes `WhoopSyncService` as a named
constructor argument and calls `self.whoop.sync_range(...)` directly
inside `run_nightly_pipeline`. `AutomationRun.whoop_summary` is a named
field on the persisted run record.

This is acceptable for one or two integrations.

### Future state

Once there are **three or more automated integrations**, introduce an
`IntegrationRegistry`:

```text
IntegrationRegistry
  - register(service: BaseConnector, account_id_provider: Callable)
  - enabled_integrations() -> list[IntegrationMetadata]
  - sync_all(start, end) -> dict[source, IntegrationSyncSummary]
  - sync_one(source, start, end) -> IntegrationSyncSummary
  - capabilities(source) -> ConnectorCapability
  - configured_accounts(source) -> list[str]
```

`AutomationService` would then call `registry.sync_all(start, end)`
instead of named services, iterate the summaries, and union the
`affected_months`.

`AutomationRun` would move from `whoop_summary: dict` to:

```python
connector_summaries: dict[str, dict[str, Any]]  # keyed by EventSource
```

This is a Mongo schema change and an API-shape change; both are
deferred until a real second integration motivates them.

### Why we are not doing this now

- We only have one automated integration (WHOOP). A registry today would
  be an abstraction without a second concrete user, violating the rule
  "two real implementations before an abstraction" (CLAUDE.md §9).
- The contract types (`IntegrationSyncSummary`,
  `ConnectorCapability`, `BaseConnector`) are already defined in
  `packages/connectors/base.py`, so a future registry can be added
  without further model changes.

### Migration order when the time comes

1. Land the second automated integration (e.g. an Apple Health bridge),
   wired the same hardcoded way WHOOP is.
2. Land the third.
3. Extract `IntegrationRegistry` and migrate WHOOP and the two new ones
   to it in one PR.
4. Migrate `AutomationRun` to `connector_summaries` with a one-time
   backfill that maps existing `whoop_summary` into the new field.
5. Update `/automation/status` to render the new shape.

---

## 17. Quick reference

| Need to do this | Look at |
|---|---|
| Add a new connector | `docs/integration_template.md` |
| Spawn a sub-agent for it | `docs/new_integration_agent_prompt.md` |
| See example feasibility writeups | `docs/integration_examples.md` |
| See the typed contract | `packages/connectors/base.py` |
| Understand nightly automation | `docs/automation.md` |
| See the reference connector | `packages/connectors/whoop/` |
| Understand persistence | `docs/persistence.md` |
