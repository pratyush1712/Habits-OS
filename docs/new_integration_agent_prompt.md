# Prompt: add a new HabitOS integration

> Copy the block below into a fresh agent session when you want to add a
> new integration (Muse, Day One, Apple Health, medication tool, a new
> wearable, etc.). Replace `<SERVICE>` with the integration name.

---

```text
You are adding a new integration to HabitOS for: <SERVICE>.

HabitOS is a small, local-first system that turns tracker data into a
calm hyperlinked monthly PDF for reMarkable 2. It has an existing
nightly automation pipeline. New integrations must conform to the
existing contract, not invent their own.

Before you write any code, do the following — in this order — and
produce a feasibility report as your first deliverable. Do not start
implementation until I approve the report.

# Read these files

1. CLAUDE.md
2. AGENTS.md
3. docs/integration_blueprint.md
4. docs/integration_template.md
5. docs/integration_examples.md
6. docs/automation.md
7. docs/persistence.md
8. docs/whoop_integration.md  (the reference connector's docs)
9. packages/connectors/base.py
10. packages/connectors/whoop/ — every file
11. apps/api/services/whoop_sync.py
12. apps/api/services/automation.py
13. apps/api/services/habit_evaluation.py
14. packages/core/models.py
15. packages/core/rules.py
16. packages/core/default_habits.py
17. packages/core/repositories/source_events.py
18. packages/core/repositories/source_accounts.py
19. packages/core/repositories/habit_entries.py

# Fetch the latest official documentation for <SERVICE>

Do not rely on memorized API knowledge. Open the official docs and read
them. Capture:

- API reference URL
- Auth model (OAuth scopes, API key, none)
- Webhook docs URL (if any)
- Rate limits and pagination
- Export/import options
- Anything that signals the service might *not* be cleanly automatable
  (no public API, undocumented endpoints, expiring credentials)

# Identify the integration type

Pick exactly one from docs/integration_blueprint.md §4:

- OAuth pull API
- API-key pull API
- Webhook push API
- Local file/export import
- iOS Shortcut bridge
- Apple Health bridge
- Manual endpoint
- Unsupported / no viable API

If the service does not have a clean API, prefer manual-first per
blueprint §4. Do not force OAuth where it does not fit.

# Identify automation compatibility

Decide every field on ConnectorCapability in
packages/connectors/base.py:

- nightly_eligible
- supports_date_range_sync
- supports_backfill
- supports_reconciliation
- recommended_reconcile_window_days
- service_revises_historical_data
- sync_is_idempotent
- required_env_vars
- graceful_when_unconfigured

If you cannot answer one of these confidently, say so in the feasibility
report and propose how to find out.

# Map service records to SourceEvent

For each external record type, propose the SourceEvent mapping. Cover:

- source       (must be an existing EventSource literal, or call out the
                model change required)
- source_event_id  (stable across reruns)
- event_type   (must be an existing EventType literal, or call out the
                model change required)
- start_time_utc, end_time_utc, local_date, timezone
- metrics      (only stable, rule-relevant fields)
- raw_payload  (full original record)
- title, description

# Identify habit / rule changes

Decide:

- Which habit key(s) does this integration feed?
- Are those habits already in packages/core/default_habits.py?
- Is the rule already in packages/core/rules.py? If not, propose the
  pure evaluator function signature and default thresholds.

# Propose exact files to change

List every file you intend to create or modify, with one sentence per
file. Suggested structure for a typical pull-API integration:

Create:
- packages/connectors/<service>/__init__.py
- packages/connectors/<service>/client.py
- packages/connectors/<service>/normalizer.py
- packages/connectors/<service>/auth.py        (if OAuth)
- packages/connectors/<service>/webhook.py     (if webhook)
- apps/api/services/<service>_sync.py
- apps/api/routes/<service>.py
- tests/connectors/test_<service>_normalizer.py
- tests/connectors/test_<service>_client.py
- tests/api/test_<service>_sync_service.py
- docs/integrations/<service>.md  (from docs/integration_template.md)

Modify:
- packages/core/models.py   (only if new EventSource/EventType literals)
- packages/core/default_habits.py  (only if new habit)
- packages/core/rules.py    (only if new rule)
- apps/api/main.py          (route wiring)
- .env.example              (new env vars)
- docs/automation.md        (only if added to nightly pipeline)
- README.md                 (only if a new user-facing command appears)

# Do not code until approved

Your first deliverable is the feasibility report:

1. Integration type
2. Automation compatibility decisions
3. SourceEvent mapping
4. Habit/rule changes needed
5. Files to create / modify
6. Risks and open questions
7. MVP recommendation (build now / defer / manual bridge first / not
   possible)

Then wait for review.

# Implementation rules once approved

- Implement only the smallest reliable MVP path. If manual bridge is the
  right MVP, ship that, not OAuth.
- Connectors must never write habit_entries. Only the rule engine or
  manual override system writes habit_entries.
- Connectors must upsert SourceEvents by (source, source_event_id).
- New service-layer connectors should match the BaseConnector Protocol
  shape in packages/connectors/base.py and return
  IntegrationSyncSummary from sync_range.
- Service-specific logic stays inside packages/connectors/<service>.
  Route handlers in apps/api/routes/<service>.py stay thin.
- Do not create a new scheduler. If the integration participates in
  nightly automation, wire it through AutomationService the same way
  WhoopSyncService is wired today.
- Add tests:
  - normalizer (pure)
  - service-layer sync_range, including an idempotency test
  - rule changes, if any
- Add docs/integrations/<service>.md from the template, and update
  .env.example.
- Do not refactor WHOOP. Do not introduce Redis, Celery, Docker, or a
  new database.

# When you are done

Summarize:
- files changed
- new env vars
- the IntegrationSyncSummary the new integration produces
- how to invoke it manually (curl)
- automation compatibility (nightly or not, and why)
- what is intentionally not included
```

---

## Notes for the human reviewing the feasibility report

- A "Manual bridge first" decision is a perfectly acceptable outcome. So
  is "Not possible." Both prevent wasted work.
- If the agent proposes adding `EventSource` or `EventType` literals,
  the change to `packages/core/models.py` must include matching test
  coverage in `tests/core/test_models.py`.
- If the agent proposes wiring into nightly automation, verify
  `graceful_when_unconfigured=True` and that the integration returns
  `skipped_reason` rather than raising when credentials are missing.
- The agent must not silently bypass the rule engine. Watch for any
  proposed write to `habit_entries` from a connector.
