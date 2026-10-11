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
| Weekly auto-grant | service `habits-autogrant`, cron `15 17 * * 6` UTC (Sunday 00:15 Asia/Bangkok) |
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

## Weekly auto-grant

`habits-autogrant [--dry-run] [--days N]` (`src/solo_habits/autogrant.py`) replaces the
retired local `weekly_habit_autogranted` job. For each active habit and each of the
last N days (default 7, ending yesterday in Asia/Bangkok) on one of its
`schedule_days` (every day when unset) without a completed log, it logs the day
(`completed: true, count: 1`, note `auto-granted (weekly batch)`). It calls this
cell's own HTTP API as the `habit-autolog` automation (`habits.habit:read|write`),
never the database, so execution and audit records apply, and streaks are
recomputed by the service. Idempotent: days with a completed log are skipped and the
log endpoint is an upsert, so re-running a week never double-logs. Zero habits is a
successful no-op. Prints one JSON line per run; exit 1 if the API fails or a day
could not be logged (retried next run), 2 on missing configuration. Variables
(Railway only): `HABITS_API_URL` (the `habits-api` public https URL),
`HABITS_AUTOGRANT_TOKEN` (the `habit-autolog` automation token; rotate with the other
cell tokens). Deploy: `railway up --ci --service habits-autogrant`; check:
`railway run --service habits-autogrant -- habits-autogrant --dry-run`.

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
