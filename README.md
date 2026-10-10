# solo-habits

The habits cell: habits and routines and their daily logs. It keeps its own
Neon database and reuses [empire-platform](https://github.com/bookchaowalit/empire-platform)
for identity, authorization, execution and audit records, and the graph, over
HTTP with the caller's own token (same pattern as
[solo-decisions](https://github.com/bookchaowalit/solo-decisions)).

| | |
|---|---|
| API | Railway project `solo-habits`, service `habits-api` (Serverless: sleeps when idle) |
| Outbox sweep | service `habits-publisher`, cron `*/15 * * * *` |
| Data | Neon project `solo-habits`, database `habits` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`habits`) |

## Rules

- Writes: recorded precheck → local change → platform execution bound to the
  exact record → commit → finish with row hashes. Fails closed (503) when the
  platform cannot answer.
- **Streaks belong to the service.** Every change to a habit's logs recomputes
  `current_streak`, `best_streak` (never lowered) and `last_completed_at` in the
  same transaction: consecutive scheduled weekdays (every day without a
  schedule) completed, walking back from today in `HABITS_TIMEZONE`
  (default Asia/Bangkok); today not yet done does not break the streak.
- Permissions: `habits.habit:read|write|delete`, `habits.routine:read|write|delete`.
  Logging or un-logging a day is a write on its habit or routine.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/habits` · `/v1/routines` | list (`status`, `category`/`frequency`, `routine_type`, paging) |
| GET | `/v1/{habits,routines}/stats` | counts by status or a filter column |
| GET | `/v1/{habits,routines}/{id}` · `/slug/{slug}` | one record |
| POST | `/v1/habits` · `/v1/routines` | create (`Idempotency-Key` supported) |
| PATCH / DELETE | `/v1/{habits,routines}/{id}` | change (`expected_version`) / delete |
| GET | `/v1/habit-logs` · `/v1/routine-logs` | logs (`habit_id`/`routine_id`, `from`, `to`, `completed`, `notes_prefix`, `order`) |
| PUT / DELETE | `/v1/{habits,routines}/{id}/logs/{date}` | log a day (upsert) / remove it |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q          # add ../empire-platform[dev] for the end-to-end test
NEON_API_KEY=... .venv/bin/habits-db provision
npm install && railway config apply && railway up --ci --service habits-api
```

Railway variables (never in the repository): `HABITS_DB_MODE=hosted`,
`HABITS_DB_URL_API` / `HABITS_DB_URL_PUBLISHER`, `HABITS_JWT_PUBLIC_KEY_PEM`,
`HABITS_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`, `HABITS_PUBLISHER_TOKEN`.
