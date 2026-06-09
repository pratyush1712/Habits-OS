# HabitOS Admin

Private operational surface for HabitOS. This app is intentionally small and
debugging-oriented: inspect source events, manually log medication/supplement dose counts and protein shakes, review resolved month state, kick
recomputes and renders, and prepare reMarkable upload instructions.

## Stack

- Next.js 16 App Router
- TypeScript
- Tailwind CSS v4
- Auth.js / `next-auth` with Google OAuth
- Server-side fetches into the FastAPI backend under `apps/api/`

## Auth model

- Google sign-in only
- Single allowed user:
  `pratyushsudhakar03@gmail.com`
- No browser-to-FastAPI calls. The browser only talks to the Next app.

## Environment

Create `apps/admin/.env.local` from `apps/admin/.env.local.example`.

Required variables:

- `AUTH_SECRET`
- `AUTH_GOOGLE_ID`
- `AUTH_GOOGLE_SECRET`
- `API_BASE_URL`

Optional:

- `API_ADMIN_KEY`

## Development

From the repo root:

```bash
make run-api
make run-admin
```

Or directly:

```bash
pnpm --dir apps/admin dev
```

## Useful scripts

```bash
pnpm --dir apps/admin dev
pnpm --dir apps/admin typecheck
pnpm --dir apps/admin lint
pnpm --dir apps/admin build
pnpm --dir apps/admin api-types
```

## Routes

Public:

- `/`
- `/login`

Private:

- `/dashboard`
- `/month/[month]`
- `/day/[date]`
- `/events`
- `/medication`
- `/protein-shake`
- `/habits`
- `/habits/[key]`
- `/automation`
- `/renders`
- `/connections`
- `/settings`

## Design notes

This app follows the design handoff in `apps/design-docs/`:

- warm paper / ink palette
- Source Serif 4 + JetBrains Mono
- custom habit status glyphs
- hairline separators instead of glossy cards
- text-first navigation and controls
