# Integration Examples

These are **sketches**, not commitments. They illustrate how the
blueprint and the connector contract apply to four candidate
integrations. None are implemented yet. Before any of them is built, a
full per-service doc from `docs/integration_template.md` must be filled
in, including current API research.

The starting assumptions below come from the project's prior decisions
(see `CLAUDE.md` §6 and `AGENTS.md` §4); they may be refined when the
integration is actually scoped.

---

## Muse (meditation)

| Field | Sketch |
|---|---|
| Likely integration type | **Apple Health bridge** first (Mindful Minutes), then manual export, then SDK only as a last resort |
| Likely `SourceEvent.event_type` | `"meditation"` (already in `EventType`) |
| Likely `SourceEvent.source` | `"muse"` (already in `EventSource`) — _or_ `"apple_health"` if routed via the bridge; choose one and document the decision |
| Likely habit mappings | `meditation` (existing default habit) |
| Default habits needed | None — `meditation` already exists |
| Rule engine changes | None — `evaluate_meditation` already handles `event_type="meditation"` |
| Likely automation compatibility | `nightly_eligible=False` initially (manual bridge); `nightly_eligible=True` only if a reliable Apple Health export job exists |
| Likely MVP path | Manual `POST /events/meditation` endpoint that accepts duration + date. Optionally accept an Apple Health export file. |
| Likely risk | Muse's official developer path is SDK/device-oriented, not a personal cloud API. A direct backend pull is unrealistic for historical sessions. Apple Health requires an iOS-side bridge. |

**Notes:**
- The user already meditates; the goal is to have those sessions show up
  without daily manual entry.
- Do not start with the Muse SDK or raw EEG (`CLAUDE.md` §13).

---

## Day One (journaling)

| Field | Sketch |
|---|---|
| Likely integration type | **Local file/export import** first, then iOS Shortcut second; OAuth only if Day One ships an official API |
| Likely `SourceEvent.event_type` | `"journal"` (already in `EventType`) |
| Likely `SourceEvent.source` | New literal needed — `EventSource` does not yet include `"day_one"`. Adding it requires updating `packages/core/models.py` per blueprint §11. |
| Likely habit mappings | `journaling` (existing default habit, currently manual-only) |
| Default habits needed | None — `journaling` already exists as manual |
| Rule engine changes | Likely yes — `journaling` is currently manual-only per CLAUDE.md §8. A new auto evaluator could mark `checked` when one or more journal events exist on the date. |
| Likely automation compatibility | `nightly_eligible=False` if file-import; `nightly_eligible=True` only if a Shortcut runs nightly |
| Likely MVP path | A FastAPI endpoint that accepts a Day One JSON export and writes one `SourceEvent` per entry. Stretch: iOS Shortcut that POSTs entry metadata when the user saves. |
| Likely risk | Day One does not publish a stable third-party API. Exports are the safe path. |

---

## Apple Health

| Field | Sketch |
|---|---|
| Likely integration type | **iOS Shortcut bridge** or HealthKit-app bridge; not a direct backend pull |
| Likely `SourceEvent.event_type` | Depends on what is forwarded — `"meditation"`, `"sleep"`, `"workout"` are all candidates |
| Likely `SourceEvent.source` | `"apple_health"` (already in `EventSource`) |
| Likely habit mappings | `meditation`, `sleep`, `workout`, possibly future `medication` if forwarded |
| Default habits needed | None for existing habits; medication would need a new habit + new `EventType` literal |
| Rule engine changes | None for existing habits |
| Likely automation compatibility | `nightly_eligible=False` — push-driven from iOS, not pulled from a backend |
| Likely MVP path | An authenticated `POST /events/apple_health` endpoint that an iOS Shortcut calls with a small JSON envelope (type, start, end, value). Server normalizes into `SourceEvent`. |
| Likely risk | Direct HealthKit access requires an iOS app. Shortcuts are reliable enough for the calm-output use case; do not over-engineer. |

---

## Smart medication management tool

| Field | Sketch |
|---|---|
| Likely integration type | **Depends on vendor.** Evaluate the actual vendor before assuming an API exists. Many medication trackers do not expose one. |
| Likely `SourceEvent.event_type` | `"medication"` exists for manual/vendor-normalized dose-count observations. |
| Likely `SourceEvent.source` | `"manual"` for local logs or `"medication"` for a future vendor-neutral connector. |
| Likely habit mappings | `medication` — aggregate scheduled-dose coverage for the day. |
| Default habits needed | Already present in `packages/core/default_habits.py`. |
| Rule engine changes | Implemented: `checked` when all explicitly observed scheduled doses are taken, `partial` for some, `missed` only when an observed scheduled day has zero taken. PRN/as-needed absence is not missed. |
| Likely automation compatibility | Depends entirely on the vendor. If a pull API exists, likely `nightly_eligible=True` with idempotent upsert. If not, manual-first. |
| Likely MVP path | Manual dose-count events first (including `/events/import-sample` fixtures). A dedicated route or iOS Shortcut can be added later without changing the core model. |
| Likely risk | **Privacy-sensitive data.** Per blueprint §15, ensure nothing identifiable is logged. Token encryption (currently deferred per `CLAUDE.md` §10) should be revisited before storing real medication credentials. |

---

## What these examples have in common

- All four are likely to start as **manual-first integrations**. That is
  the blueprint's first-class pattern, not a fallback.
- Three of the four require literal-union changes in
  `packages/core/models.py` (Day One source, medication source and
  event type).
- Only Muse can reuse every existing habit, event type, and rule
  without any core changes.
- None of the four should be added to nightly automation in their
  first MVP. Nightly eligibility is a graduation criterion, not a
  starting condition.

When any of these is actually scoped, the agent doing the work should
fill in `docs/integrations/<service>.md` from
`docs/integration_template.md` and stop at "feasibility report" before
writing code.
