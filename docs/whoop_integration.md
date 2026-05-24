# WHOOP integration

Milestone 4 adds a small pull-based WHOOP connector. The first implementation
intentionally avoids webhooks and nightly scheduling until manual date-range
sync works end to end.

## Official references checked

- API reference: <https://developer.whoop.com/api/>
- OAuth 2.0: <https://developer.whoop.com/docs/developing/oauth>
- Pagination: <https://developer.whoop.com/docs/developing/pagination>
- Rate limits: <https://developer.whoop.com/docs/developing/rate-limiting>
- Webhooks: <https://developer.whoop.com/docs/developing/webhooks/>

## OAuth

WHOOP uses OAuth 2.0 authorization-code flow.

- Authorization URL: `https://api.prod.whoop.com/oauth/oauth2/auth`
- Token URL: `https://api.prod.whoop.com/oauth/oauth2/token`
- Refresh tokens require the `offline` scope.
- Refresh token use rotates both access and refresh tokens; persist the new pair
  immediately and avoid concurrent refreshes for the same account.

HabitOS defaults to these scopes:

```text
offline read:workout read:sleep read:recovery read:profile
```

`read:profile` is used to discover the WHOOP `user_id` during OAuth callback so
`source_accounts._id` can be `whoop:{user_id}`.

## Endpoints used

All collection endpoints are paginated with `limit <= 25`, `start`, `end`, and
`nextToken`.

- Workouts: `GET /developer/v2/activity/workout`
- Sleep: `GET /developer/v2/activity/sleep`
- Recovery: `GET /developer/v2/recovery`
- Profile: `GET /developer/v2/user/profile/basic`

## Local API flow

1. `GET /whoop/oauth/start` returns an authorization URL and state.
2. User authorizes the app in WHOOP.
3. `POST /whoop/oauth/callback?code=...` exchanges the code, fetches profile,
   and stores a `SourceAccount` through `SourceAccountsRepo`.
4. `POST /whoop/sync?external_user_id=...&start=YYYY-MM-DD&end=YYYY-MM-DD`
   fetches workouts/sleeps/recoveries, normalizes them to `SourceEvent`, writes
   through `SourceEventsRepo`, marks `last_sync_at`, and recomputes affected
   months by calling `HabitEvaluationService`.

## Normalization

WHOOP raw payloads are preserved in `SourceEvent.raw_payload`. Stable values used
by rules/rendering are copied into `metrics`.

- Workout events use WHOOP workout UUID as `source_event_id`.
- Sleep events use WHOOP sleep UUID as `source_event_id`.
- Recovery events use `recovery:{sleep_id}` when available, otherwise
  `recovery:cycle:{cycle_id}`.
- Sleep/recovery local dates are anchored with WHOOP `timezone_offset`; recovery
  prefers the associated sleep start when the sleep was fetched in the same
  sync window.

## Rate limits

Default WHOOP limits are 100 requests/minute and 10,000 requests/day. WHOOP
returns `X-RateLimit-*` headers and `429` when limited. HabitOS keeps syncs
manual and date-bounded for now; future scheduler jobs should reconcile only a
small recent window, e.g. 7-14 days.

## Webhooks later

WHOOP webhooks are notifications, not data payloads. v2 webhook events include
`workout.updated/deleted`, `sleep.updated/deleted`, and
`recovery.updated/deleted`. v2 recovery webhook IDs refer to the associated
sleep UUID. A future endpoint must validate `X-WHOOP-Signature` and
`X-WHOOP-Signature-Timestamp` using:

```text
base64(HMACSHA256(timestamp_header + raw_http_request_body, client_secret))
```

Respond `2XX` quickly, process asynchronously, dedupe by `trace_id`, and keep a
reconciliation job because webhook delivery can duplicate or miss events.
