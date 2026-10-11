"""habits-autogrant: HTTP behaviour against a fake habits API (no database)."""

import json
from datetime import date

import pytest

from solo_habits import autogrant
from solo_habits.autogrant import ApiError, run

TODAY = date(2026, 10, 11)  # a Sunday; the window is Sun 10-04 .. Sat 10-10


class FakeHttp:
    def __init__(self, habits, logs=(), fail_dates=()):
        self.habits, self.logs, self.fail_dates, self.puts = habits, list(logs), set(fail_dates), []

    def call(self, method, path, body=None, params=None):
        if method == "GET" and path == "/v1/habits":
            assert params["status"] == ["active"]
            return {"items": self.habits}
        if method == "GET" and path == "/v1/habit-logs":
            assert params["completed"] == "true" and params["to"] == "2026-10-10"
            return {"items": self.logs}
        assert method == "PUT"
        stamp = path.rsplit("/", 1)[1]
        if stamp in self.fail_dates:
            raise ApiError(500, "PUT x")
        key = (int(path.split("/")[3]), stamp)
        self.puts.append((key, body))
        existed = any((l["habit_id"], l["log_date"]) == key for l in self.logs)
        if not existed:
            self.logs.append({"habit_id": key[0], "log_date": stamp, "completed": True})
        return {"outcome": "unchanged" if existed else "created", "log": {}}


def habit(i, days=None):
    return {"id": i, "name": f"h{i}", "schedule_days": days}


def test_zero_habits_is_a_clean_noop():
    http = FakeHttp([])
    assert run(http, TODAY, 7, dry_run=False) == {"habits": 0, "granted": 0, "skipped": 0, "errors": 0}
    assert http.puts == []


def test_grants_every_scheduled_missing_day_with_note():
    http = FakeHttp([habit(1), habit(2, ["mon", "fri"])])
    counts = run(http, TODAY, 7, dry_run=False)
    assert counts["granted"] == 9 and counts["skipped"] == 0  # 7 + (Mon 10-05, Fri 10-09)
    assert ((2, "2026-10-05"), {"completed": True, "count": 1, "notes": autogrant.NOTE}) in http.puts
    assert not any(k == (2, "2026-10-06") for k, _ in http.puts)


def test_existing_completed_days_are_skipped():
    logs = [{"habit_id": 1, "log_date": "2026-10-09", "completed": True}]
    http = FakeHttp([habit(1)], logs)
    counts = run(http, TODAY, 7, dry_run=False)
    assert counts["granted"] == 6 and counts["skipped"] == 1


def test_rerun_same_week_never_double_logs():
    http = FakeHttp([habit(1), habit(2)])
    run(http, TODAY, 7, dry_run=False)
    first = len(http.puts)
    second = run(http, TODAY, 7, dry_run=False)
    assert len(http.puts) == first and second["granted"] == 0 and second["skipped"] == 14


def test_dry_run_writes_nothing():
    http = FakeHttp([habit(1)])
    assert run(http, TODAY, 7, dry_run=True)["granted"] == 7
    assert http.puts == []


def test_failed_day_is_counted_and_others_continue():
    http = FakeHttp([habit(1)], fail_dates={"2026-10-08"})
    counts = run(http, TODAY, 7, dry_run=False)
    assert counts["errors"] == 1 and counts["granted"] == 6


def test_main_exit_codes_and_no_token_in_output(monkeypatch, capsys):
    monkeypatch.delenv("HABITS_API_URL", raising=False)
    monkeypatch.delenv("HABITS_AUTOGRANT_TOKEN", raising=False)
    assert autogrant.main([]) == 2
    assert json.loads(capsys.readouterr().out)["missing"] == ["HABITS_API_URL", "HABITS_AUTOGRANT_TOKEN"]

    monkeypatch.setenv("HABITS_API_URL", "https://habits.example")
    monkeypatch.setenv("HABITS_AUTOGRANT_TOKEN", "sekrit-token")
    monkeypatch.setattr(autogrant, "Http", lambda base, token: FakeHttp([]))
    assert autogrant.main(["--dry-run"]) == 0
    line = json.loads(capsys.readouterr().out)
    assert line["event"] == "habits.autogrant" and line["habits"] == 0 and line["dry_run"] is True

    down = FakeHttp([])
    down.call = lambda *a, **k: (_ for _ in ()).throw(ApiError(503, "GET /v1/habits"))
    monkeypatch.setattr(autogrant, "Http", lambda base, token: down)
    assert autogrant.main([]) == 1
    out = capsys.readouterr()
    assert "sekrit-token" not in out.out + out.err


def test_days_bounds_and_https_only():
    with pytest.raises(SystemExit):
        autogrant.main(["--days", "0"])
    with pytest.raises(SystemExit):
        autogrant.Http("http://habits.example", "t")
    autogrant.Http("http://localhost:3000", "t")
