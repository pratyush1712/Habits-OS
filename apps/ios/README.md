# HabitOS iOS

Native SwiftUI companion app for HabitOS. It is intentionally small: it reads the backend month state, shows today's resolved habit entries, and writes medication/supplement dose counts, protein counts, and product-level intake logs to the existing HabitOS endpoints.

## Open in Xcode

```bash
open apps/ios/HabitOS.xcodeproj
```

The project targets iPhone, iOS 18+, Swift 6, and uses no third-party packages.

## API setup

The app defaults to the deployed admin mobile API:

```text
https://habits.pratyushsudhakar.com/api/mobile
```

That URL works from both Simulator and a physical iPhone after the matching `apps/admin/app/api/mobile/*` routes are deployed. If `HABITOS_MOBILE_API_KEY` is configured on Vercel, paste the same value into the app's Settings tab; otherwise leave the mobile key blank.

## What the app calls

- `GET /api/mobile/state/month?month=YYYY-MM` loads habits, habit entries, medication schedule metadata, and logged medication days.
- `POST /api/mobile/events/medication` saves one idempotent source event per medication/supplement for the selected local date.
- `POST /api/mobile/events/protein` saves an idempotent `protein_shake` source event with the day's protein serving count for the selected local date. `/api/mobile/events/protein-shake` remains as a compatibility alias.
- `POST /api/mobile/events/intake` saves idempotent ingredient source events for the selected product bundle; individual ingredients live behind an advanced selector.
- `POST /api/mobile/habits/recompute?month=YYYY-MM` optionally refreshes persisted habit entries after a medication, protein, or intake save.

The backend remains the source of truth. The mobile app does not maintain an independent medication, protein, or intake database.
