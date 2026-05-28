# reMarkable 2 sync

HabitOS treats the reMarkable 2 as a calm output surface. The backend database
and generated PDF remain the source of truth; the tablet receives replaceable,
machine-owned artifacts only.

## Safety rules

- Do not directly edit reMarkable notebook internals in v1.
- Do not overwrite human-owned handwritten notebooks.
- Keep generated dashboards under machine-owned paths only:
  - current month (device home screen):
    `01. Habit Tracker.pdf`
  - archived month:
    `HabitOS / YYYY / Archive / YYYY-MM Habit Dashboard.pdf`
- Manual upload is the default and safest sync path.
- USB web interface and cloud tooling are optional adapters after manual sync is
  working and tested.
- SSH/local access is advanced-only and should remain isolated behind an adapter.

## Selecting an adapter

HabitOS supports two adapters. Switch with `HABITOS_REMARKABLE_ADAPTER`:

| Value              | Behavior                                                                        |
| ------------------ | ------------------------------------------------------------------------------- |
| `manual` (default) | Returns upload instructions only. Never mutates device or cloud state.          |
| `rmapi`            | Performs automated reMarkable Cloud sync by shelling out to the ddvk/rmapi CLI. |

The selected adapter is used by `RemarkableSyncService` (the
`/remarkable/*` routes) **and** by `RemarkableLifecycleService` (the
nightly automation upload step). Both go through the same factory in
`apps/api/deps.py`.

## Current adapter: manual

The manual adapter validates that a generated PDF exists and returns upload
instructions. It does not mutate the device or cloud state.

Typical flow:

1. Render a month with `POST /render/month?month=YYYY-MM`.
2. HabitOS stores the generated path in `RenderJob.output_path`.
3. Call `POST /remarkable/sync?month=YYYY-MM&dry_run=true`.
4. Follow the returned instructions:
   - On the reMarkable 2, enable Settings → Storage → USB web interface.
   - Connect over USB.
   - Open `http://10.11.99.1/`.
   - Upload the current month PDF to the device home screen as
     `01. Habit Tracker.pdf`.

The sync service reads `RenderJobsRepo.latest_for_month(month)` and uses only the
stored `output_path`. It does not call or modify the PDF renderer.

## Current and archive lifecycle

HabitOS keeps the current month easy to find while still organizing old months.

- Current month (home screen):
  `01. Habit Tracker.pdf`
- Archived month:
  `HabitOS / YYYY / Archive / YYYY-MM Habit Dashboard.pdf`

Monthly rollover behavior:

1. Render/finalize the previous month.
2. Prepare/archive the previous month under the year archive path.
3. Render the new current month.
4. Keep the new month visible on the home screen as `01. Habit Tracker`.

Archived months are treated as frozen after they leave the reconcile window.
If the previous month is still inside the rolling WHOOP reconcile window,
HabitOS may re-render and refresh that archived month so late sleep/recovery
settling is preserved.

## Researched options

### Manual upload

Safest first path. It works with the reMarkable desktop/mobile apps or the USB
web interface and avoids unofficial API writes.

### USB web interface

The community-maintained reMarkable Guide documents a local web interface at
`http://10.11.99.1/` when enabled on the tablet. It exposes endpoints such as:

- `GET /documents/`
- `GET /documents/{guid}`
- `POST /upload`
- `GET /download/{guid}/pdf`

This is a good future local adapter, but folder/upload behavior is subtle: the
upload endpoint targets the last folder listed. A safe implementation should
start with list-only and upload-only into an already-confirmed machine-owned
folder.

### rmcl

`rmcl` is an unofficial Python reMarkable Cloud library. It supports a file-tree
view, metadata, create/update/delete, and uploads. It handles cloud tokens, but
uses Trio and an unofficial cloud API, so it is a later adapter rather than the
first automation path.

### rmapi (ddvk fork) — the first automated adapter

The original juruen/rmapi is archived. HabitOS uses the
actively-maintained ddvk fork at <https://github.com/ddvk/rmapi> as the
first automated cloud sync adapter. It is a Go CLI with non-interactive
commands (`ls`, `mkdir`, `stat`, `put`) that map cleanly onto HabitOS's
machine-owned folder model and require no platform-specific code on the
HabitOS side.

See `## Automated adapter: rmapi` below for setup and operation.

### rmapy

`rmapy` is an unofficial Python cloud API client. Its repository is archived and
old; avoid for new implementation.

### SSH/local access

SSH provides powerful root access over USB or Wi-Fi. It is useful for advanced
experiments, but too risky for the MVP because it can modify internal device
state. Do not use SSH for generated PDF sync unless explicitly tested and
isolated behind a conservative adapter.

---

## Automated adapter: rmapi

The `rmapi` adapter (`packages/remarkable_sync/rmapi.py`) shells out to
the ddvk/rmapi CLI to push generated PDFs to the reMarkable Cloud. It is
conservative by design.

### Why rmapi

- Only currently-maintained CLI for the reMarkable Cloud that supports
  the required commands non-interactively.
- Pure subprocess — no Python bindings to drift, no extra service.
- Idempotent commands map cleanly onto HabitOS's machine-owned folders.
- HabitOS shells out rather than linking, so the AGPL-3.0 license of
  rmapi is not a concern; users install rmapi themselves.

### Install rmapi (one-time)

Pick one:

```bash
# 1. Prebuilt binary (recommended on macOS/Linux)
# Download from https://github.com/ddvk/rmapi/releases and put on PATH.

# 2. Build from source
git clone https://github.com/ddvk/rmapi
cd rmapi && go install
# Binary lands in $HOME/go/bin/rmapi.

# 3. Docker (skip for HabitOS; the adapter assumes a direct binary).
```

### Authenticate rmapi (one-time, interactive)

HabitOS cannot do this for you. rmapi requires pasting a one-time code
from <https://my.remarkable.com/device/desktop/connect>:

```bash
# Recommended: dedicated config so HabitOS sync uses an isolated token.
mkdir -p ~/.config/habitos
RMAPI_CONFIG=~/.config/habitos/rmapi.conf rmapi
# rMAPI will prompt for a one-time code. Paste it. Tokens persist in the
# specified config file.
```

After this is done, point HabitOS at the same config file (see env vars
below).

### Required env vars

| Variable                                 | Purpose                                  | Default                              |
| ---------------------------------------- | ---------------------------------------- | ------------------------------------ |
| `HABITOS_REMARKABLE_ADAPTER`             | `manual` or `rmapi`                      | `manual`                             |
| `HABITOS_RMAPI_BINARY`                   | Binary name or absolute path             | `rmapi`                              |
| `HABITOS_RMAPI_CONFIG_PATH`              | Path to dedicated rmapi config file      | _(empty → rmapi default `~/.rmapi`)_ |
| `HABITOS_RMAPI_TIMEOUT_SECONDS`          | Per-command timeout                      | `60`                                 |
| `HABITOS_RMAPI_TRACE`                    | Forward `RMAPI_TRACE=1` to rmapi         | `false`                              |
| `HABITOS_RMAPI_PRESERVE_ANNOTATIONS`     | Refresh current month while keeping ink  | `true`                               |
| `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT` | Replace current month, dropping ink      | `false`                              |
| `HABITOS_REMARKABLE_MACHINE_ROOT`        | Top-level folder HabitOS may write to    | `HabitOS`                            |

Typical local setup:

```bash
HABITOS_REMARKABLE_ADAPTER=rmapi
HABITOS_RMAPI_BINARY=/Users/praty/go/bin/rmapi
HABITOS_RMAPI_CONFIG_PATH=~/.config/habitos/rmapi.conf
HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=false
HABITOS_REMARKABLE_DRY_RUN=true   # flip to false once the dry-run plan looks right
```

### Dry-run vs real upload

- `dry_run=true` (and `HABITOS_REMARKABLE_DRY_RUN=true` for nightly):
  the adapter never spawns rmapi. It returns `status="planned"` with the
  exact argv it would have executed in `instructions`.
- `dry_run=false`: the adapter creates the folder chain if missing,
  checks whether the target document already exists via `rmapi stat`,
  then runs `rmapi put` (with or without `--force`).

Both behaviors are visible in `/remarkable/upload?dry_run=...` and in
nightly automation summaries under `automation_runs.remarkable_summary`.

### Updating the current month without losing annotations

By default (`HABITOS_RMAPI_PRESERVE_ANNOTATIONS=true`) HabitOS refreshes the
current-month dashboard **in place, keeping your handwriting**. This is the
recommended day-to-day mode and what the nightly job uses.

A reMarkable document is not just a PDF — it is a bundle (`.rmdoc`) containing
the base PDF, a `.content` file listing one page UUID per page, and one `.rm`
ink file per annotated page, anchored to those UUIDs. `rmapi put` (with or
without `--force`) always *recreates* the document from a bare PDF, which throws
the ink away. So instead of a plain re-upload, the merge flow does:

1. `rmapi ls /` to resolve the current-month document (see naming below).
2. `rmapi get` the existing `.rmdoc` bundle.
3. Swap **only** the base PDF blob for the freshly rendered one, leaving
   `.content` (the page UUIDs) and every `.rm` ink file byte-for-byte unchanged.
4. `rmapi put --force` the rebuilt bundle, which now carries both the new data
   layer and the original ink.

**Hard requirement: the layout must be page-stable.** Annotations are positioned
per page, so the rendered PDF must have the **same page count and page order** as
what is already on the device. HabitOS enforces this: if the rendered page count
differs from the device bundle's `pageCount`, the sync **aborts with
`status="unsupported"` and does not upload anything** — protecting your ink
rather than risking misplacement. The renderer is page-stable for a given month
(page count is pure calendar math, independent of how much data exists or the
current date), so normal daily refreshes pass this check. Changing the templates
in a way that adds/removes pages will trip it; do template changes before a month
accumulates annotations, or reset that month (below).

What this means in practice:

- Past day pages: data is frozen, your annotations stay.
- Future day pages: no ink yet; their data simply updates.
- Current day / week-review page: data updates daily; any ink you add stays
  anchored as long as the layout doesn't reflow.
- The week **plan** page is intentionally data-free (pure planning space); the
  week's per-day data lives on the week **review** page.

#### Current-month document naming

`rmapi` addresses documents by their visible name, not a path with a `.pdf`
extension. The merge resolves the target by parsing `rmapi ls /` and matching a
home-screen document named exactly `01. Habit Tracker` **or** prefixed by it
(e.g. `01. Habit Tracker | May 2026`). If none matches, a new document named
`01. Habit Tracker` is created. If more than one matches ambiguously, the sync
refuses (`status="unsupported"`) rather than guess which document holds your ink
— rename or remove the extras so exactly one matches.

#### Resetting a month (dropping ink on purpose)

Set `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true` to force a clean replace of the
current month, discarding annotations. This takes precedence over
`HABITOS_RMAPI_PRESERVE_ANNOTATIONS`. Use it when you deliberately change the
layout/page count, or want a fresh page.

#### One-time end-to-end validation

The bundle round-trip is verified, but to confirm real ink survival on your own
device the first time: make a single pen stroke on the current dashboard, run a
real sync, and confirm the stroke is still there afterwards.

### Safety model

The adapter is intentionally narrow:

- Path allowlist: only the home-screen document `01. Habit Tracker` and
  `HabitOS/<YYYY>/Archive/...` are accepted. Anything else returns
  `status="unsupported"` and the adapter does not spawn rmapi.
- Archive paths are frozen. If the archive document already exists the
  adapter refuses to overwrite, regardless of `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT`.
- Current-month default is non-destructive. When the dashboard already
  exists, the adapter refreshes it via the annotation-preserving merge
  (see above) instead of overwriting it.
- Destructive replace is gated. `put --force` on the current month only
  happens when `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true`, and it
  drops annotations by design.
- Page-count guard. The merge aborts (`status="unsupported"`, no upload)
  if the rendered PDF's page count differs from the device document, so
  a layout change can never silently misplace ink.
- Commands the adapter never runs against arbitrary paths: `rm`, `mv`,
  `geta`, `mput`, `mget`, `find`. (`get` and `put --force` are used only
  on the resolved machine-owned current-month document during a merge.)
- The binary path is validated. A missing binary surfaces as
  `status="not_configured"` with a clear diagnostic, not a stack trace.
- Subprocess timeouts are recorded as `status="failed"` — they do not
  hang the API or the nightly run.

### Status diagnostics

```bash
curl http://127.0.0.1:8083/remarkable/status
```

When `HABITOS_REMARKABLE_ADAPTER=rmapi` the payload includes an `rmapi`
block:

```jsonc
{
  "adapter": "rmapi",
  "mode": "automated_cloud",
  "rmapi": {
    "binary": "/Users/praty/go/bin/rmapi",
    "binary_path": "/Users/praty/go/bin/rmapi",
    "binary_available": true,
    "config_path": "/Users/praty/.config/habitos/rmapi.conf",
    "config_path_readable": true,
    "authenticated": true,
    "ls_returncode": 0,
    "trace": false,
    "replace_existing_current": false,
    "preserve_annotations": true,
    "machine_root": "HabitOS",
    "timeout_seconds": 60,
  },
}
```

`authenticated: false` with a non-zero `ls_returncode` means rmapi runs
but cannot reach the cloud — usually a token problem. Re-run the
interactive auth.

### Known limitations

- One-time auth must be done manually; HabitOS cannot script it.
- No retries this milestone. A single failure surfaces; the nightly run
  records it and continues.
- Behavior of `rmapi mkdir` on an existing folder and `rmapi stat` on a
  missing path is treated defensively (we check `stat` before deciding
  to `mkdir`, and treat exit≠0 + empty stdout as "absent"). Verify on
  your first real run that the plan in `/remarkable/upload?dry_run=true`
  matches what you expect before flipping `HABITOS_REMARKABLE_DRY_RUN`
  to `false`.
- Annotation preservation is done by rewriting the `.rmdoc` bundle (swap
  the base PDF, keep `.content` + `.rm`), not by rmapi's `--content-only`
  flag. In the pinned ddvk build, `put --content-only` is documented as
  "recreates document" — identical to `--force` — so it does **not**
  preserve ink and is not used.
- Annotation preservation depends on a page-stable layout. If you change
  the renderer's page count/order while a month already has ink, the
  merge will refuse; reset that month with
  `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true` (dropping ink) or finish
  the month first.

### Falling back to manual

Set `HABITOS_REMARKABLE_ADAPTER=manual` and restart the API. Routes and
automation revert to the non-mutating manual adapter immediately. The
rmapi binary and config file can stay in place; nothing references
them.

### Troubleshooting

- **"rmapi binary not found"** — Set `HABITOS_RMAPI_BINARY` to an
  absolute path. `which rmapi` to find it.
- **`authenticated: false` in `/remarkable/status`** — Re-run rmapi
  interactively with the same `RMAPI_CONFIG` you've pointed HabitOS at
  and paste a fresh code from
  <https://my.remarkable.com/device/desktop/connect>.
- **`status="failed"` with timeout message** — Increase
  `HABITOS_RMAPI_TIMEOUT_SECONDS` or check network connectivity to the
  reMarkable Cloud.
- **`status="unsupported"` on the current month, "page count" message** —
  The rendered PDF has a different page count than the document on the
  device, so the annotation-preserving merge refused (nothing was
  uploaded). This happens after a layout/template change. Finish the
  month, or reset it with `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true`
  (drops ink), then sync again.
- **`status="unsupported"` on the current month, "Multiple ... match"** —
  More than one home-screen document matches `01. Habit Tracker`. Rename
  or remove the extras so exactly one matches, then sync again.
- **`status="unsupported"` on the current month, "both ... false"** —
  The document exists but both `HABITOS_RMAPI_PRESERVE_ANNOTATIONS` and
  `HABITOS_RMAPI_REPLACE_EXISTING_CURRENT` are false. Enable preserve
  (keeps ink) or replace (drops ink).
- **`status="unsupported"` on an archive month** — Archives are frozen
  by design. Delete on-device if a re-archive is truly intended.
