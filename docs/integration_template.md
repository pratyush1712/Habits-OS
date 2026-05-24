# HabitOS Integration: <Service Name>

> **How to use this template:**
> Copy this file to `docs/integrations/<service>.md` and fill in every
> section. Sections that do not apply must be answered with "N/A — <one
> sentence reason>", not deleted. The integration agent prompt
> (`docs/new_integration_agent_prompt.md`) refers to these section names
> verbatim.

---

## 1. Service name

<Service display name, e.g. "Muse Meditation">

## 2. Desired HabitOS use case

One paragraph. What habit(s) does this service feed? What does the user
actually want to see on the reMarkable dashboard because of this
integration?

## 3. Official documentation links

- API reference:
- Auth / OAuth docs:
- Webhook docs:
- Rate-limit docs:
- Export/import docs:

If the service has no official docs, write "None — service does not
publish developer docs" and proceed to §4.

## 4. Unofficial / community documentation links

Only include if needed (e.g. reMarkable Cloud community libraries). Note
the unreliability risk for each.

## 5. Integration feasibility decision

One of:

- **Build now** — service has a usable path and habit mapping is clear.
- **Defer** — usable path exists but not worth building yet.
- **Manual bridge first** — start with manual endpoint / file import /
  Shortcut; revisit API later.
- **Not possible** — no viable path. Document why.

## 6. Integration type

One of (see `docs/integration_blueprint.md` §4):

- OAuth pull API
- API-key pull API
- Webhook push API
- Local file/export import
- iOS Shortcut bridge
- Apple Health bridge
- Manual endpoint
- Unsupported / no viable API

## 7. Authentication model

- Type: <`AuthType` enum value from `packages/connectors/base.py`>
- Scopes (if OAuth):
- Token lifetime:
- Refresh flow:
- Token storage: `SourceAccountsRepo` (`bytes`, future-encryptable)
- Required env vars:

## 8. Account identity model

- External user identifier field:
- Display name field:
- Multi-account support (yes / no):
- `external_user_id` used as: ...

## 9. Available data

Bullet the record types this integration produces and the fields
HabitOS will actually use.

## 10. Missing / unavailable data

What HabitOS cannot get from this service that would have been nice to
have.

## 11. Rate limits

- Per-minute:
- Per-hour:
- Per-day:
- Backoff strategy: ...

## 12. Pagination

How the integration pages through historical data, if applicable.

## 13. Webhook support

- Supported: yes / no
- Signature scheme:
- Verification location: `packages/connectors/<service>/webhook.py`
- Retry / dedupe strategy:
- After receipt: which API endpoint is called to fetch the full record?

## 14. Export / import support

If the service offers an export, document the format and what HabitOS
expects (path, content type, max size, schema).

## 15. Privacy / security concerns

Especially relevant for health, medication, or sensitive behavior data.
Note anything that should not be persisted in `raw_payload`.

## 16. Required env vars

List every variable. Each must also be added to `.env.example`.

```text
<SERVICE>_CLIENT_ID
<SERVICE>_CLIENT_SECRET
<SERVICE>_REDIRECT_URI
...
```

## 17. Data mapping to `SourceEvent`

For each external record type → `SourceEvent`:

| External field | `SourceEvent` field | Notes |
|---|---|---|
| `id` | `source_event_id` | stable across reruns |
| ... | ... | ... |

- `event_type` chosen: ...
- `local_date` computation rule: ...
- `metrics` keys: ...
- `raw_payload`: full original record

## 18. Habit mappings

Which habit keys this integration's data feeds:

| Habit key | Driven by event_type | Rule notes |
|---|---|---|
| ... | ... | ... |

## 19. Default habits needed

- Does `packages/core/default_habits.py` need a new entry? yes / no
- If yes, propose the entry verbatim.

## 20. Rule engine changes needed

- New evaluator function in `packages/core/rules.py`? yes / no
- If yes, function signature, default thresholds, and references to the
  existing pattern (workout / sleep / meditation).
- Tests in `tests/core/test_rules.py`?

## 21. Backfill behavior

- Supported: yes / no
- Maximum historical window:
- Cost of a full backfill:

## 22. Reconciliation behavior

- Service revises historical records? yes / no
- Recommended reconcile window: ___ days
- Idempotency key: `source` + `source_event_id`

## 23. Automation compatibility

Fill in the `ConnectorCapability` values verbatim:

```python
ConnectorCapability(
    nightly_eligible=...,
    supports_date_range_sync=...,
    supports_backfill=...,
    supports_reconciliation=...,
    recommended_reconcile_window_days=...,
    service_revises_historical_data=...,
    sync_is_idempotent=...,
    required_env_vars=[...],
    graceful_when_unconfigured=...,
)
```

## 24. Error handling

- Surface vs swallow decisions (see blueprint §10):
- Retries / backoff:
- What does `sync_range` return when the integration is disabled or
  unconfigured? (`skipped_reason=...`)

## 25. API routes

Proposed FastAPI routes:

- `GET /<service>/status`
- `POST /<service>/sync?start=...&end=...`
- `GET /<service>/oauth/start` (if OAuth)
- `GET /<service>/oauth/callback` (if OAuth)
- `POST /<service>/webhook` (if webhook)
- `POST /events/<service>` (if manual endpoint)

Route handlers stay thin. Logic lives in
`apps/api/services/<service>_sync.py`.

## 26. Tests

Required test files:

- `tests/connectors/test_<service>_normalizer.py`
- `tests/connectors/test_<service>_client.py` (if HTTP)
- `tests/connectors/test_<service>_auth.py` (if OAuth)
- `tests/connectors/test_<service>_webhook.py` (if webhook)
- `tests/api/test_<service>_sync_service.py` — must include an
  idempotency test (run twice, assert no duplicate events).

## 27. Docs to update

- [ ] `docs/integrations/<service>.md` (this file)
- [ ] `.env.example`
- [ ] `docs/automation.md` (if added to the nightly pipeline)
- [ ] `README.md` (only if a new user-facing command appears)

## 28. MVP recommendation

The smallest reliable version of this integration. Describe in plain
English what the user would see after MVP ships.

## 29. Decision

One of, with one paragraph of justification:

- **Build now**
- **Defer**
- **Manual bridge first**
- **Not possible**
