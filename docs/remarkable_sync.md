# reMarkable 2 sync

HabitOS treats the reMarkable 2 as a calm output surface. The backend database
and generated PDF remain the source of truth; the tablet receives replaceable,
machine-owned artifacts only.

## Safety rules

- Do not directly edit reMarkable notebook internals in v1.
- Do not overwrite human-owned handwritten notebooks.
- Keep generated dashboards under a machine-owned path:
  `HabitOS / YYYY / YYYY-MM Habit Dashboard.pdf`.
- Manual upload is the default and safest sync path.
- USB web interface and cloud tooling are optional adapters after manual sync is
  working and tested.
- SSH/local access is advanced-only and should remain isolated behind an adapter.

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
   - Upload the generated PDF as `YYYY-MM Habit Dashboard.pdf` under
     `HabitOS / YYYY`.

The sync service reads `RenderJobsRepo.latest_for_month(month)` and uses only the
stored `output_path`. It does not call or modify the PDF renderer.

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

### rmapi

`rmapi` is a Go CLI for the reMarkable Cloud API with non-interactive commands
such as `ls`, `mkdir`, and `put`. The repository is archived and notes that new
sync protocol support was experimental, so HabitOS should not depend on it for
Milestone 5.

### rmapy

`rmapy` is an unofficial Python cloud API client. Its repository is archived and
old; avoid for new implementation.

### SSH/local access

SSH provides powerful root access over USB or Wi-Fi. It is useful for advanced
experiments, but too risky for the MVP because it can modify internal device
state. Do not use SSH for generated PDF sync unless explicitly tested and
isolated behind a conservative adapter.
