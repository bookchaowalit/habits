"""MCP server tests: fake HTTP transport, no database and no network."""

import asyncio

import httpx
import pytest

from solo_habits import mcp_server as mod
from solo_habits.mcp_server import build_server

API_KEY = "EMPIRE_HABITS_API"
READS = {"habits.habit.list", "habits.habit.get", "habits.habit.streaks", "habits.habit.stats", "habits.habit.logs",
         "habits.routine.list", "habits.routine.get", "habits.routine.stats", "habits.routine.logs"}
WRITES = {"habits.habit.log", "habits.routine.log"}
ARGS = {"habits.habit.get": {"id": 1}, "habits.routine.get": {"id": 2},
        "habits.habit.log": {"habit_id": 1, "log_date": "2026-10-12", "completed": True},
        "habits.routine.log": {"routine_id": 2, "log_date": "2026-10-12", "mood_after": 4}}
SAMPLES = [
    ("habits.habit.list", {"status": ["active"], "limit": 5}, "GET", "/v1/habits", {"status": "active", "limit": "5", "offset": "0"}),
    ("habits.habit.get", {"id": 7}, "GET", "/v1/habits/7", {}),
    ("habits.habit.logs", {"habit_id": 7, "date_from": "2026-10-01"}, "GET", "/v1/habit-logs",
     {"habit_id": "7", "from": "2026-10-01", "order": "desc", "limit": "100", "offset": "0"}),
    ("habits.habit.log", {"habit_id": 7, "log_date": "2026-10-12", "count": 2, "if_absent": True}, "PUT",
     "/v1/habits/7/logs/2026-10-12", {"if_absent": "true"}),
]


def test_streaks_projects_only_streak_fields():
    fake = Fake(body={"items": [{"id": 1, "name": "run", "slug": "run", "status": "active", "current_streak": 3,
                                 "best_streak": 9, "last_completed_at": None, "notes": "private"}]})
    out = call(server(fake), "habits.habit.streaks")
    text = out.content[0].text
    assert '"current_streak": 3' in text and "private" not in text


IDENTITY = {"actor": "x", "workspace_id": "w", "workspace": "w", "tenant_id": "t", "delegation": "d", "token": "t",
            "authorization": "Bearer x", "sub": "s"}


class Fake:
    """A fake HTTP transport: records every request and answers with ``body``."""

    def __init__(self, status: int = 200, body: object | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.status, self.body = status, {"items": []} if body is None else body

    def client(self) -> httpx.Client:
        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return httpx.Response(self.status, json=self.body)
        return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://api.test")


def server(fake: Fake, read_only: bool = False):
    return build_server(fake.client(), lambda: "tok-123", read_only=read_only).server


def call(srv, name: str, args: dict | None = None):
    return asyncio.run(srv.call_tool(name, args or {}))


def names(srv) -> set[str]:
    return {tool.name for tool in asyncio.run(srv.list_tools())}


def test_tools_list_matches_the_contract():
    srv = server(Fake())
    assert names(srv) == READS | WRITES
    for tool in asyncio.run(srv.list_tools()):
        assert tool.input_schema["additionalProperties"] is False


def test_read_only_registers_only_read_tools():
    assert names(server(Fake(), read_only=True)) == READS


def test_unknown_arguments_are_rejected_before_any_http_call():
    fake = Fake()
    srv = server(fake)
    for name in sorted(READS | WRITES):
        with pytest.raises(Exception, match="invalid_arguments: surprise"):
            call(srv, name, {**ARGS.get(name, {}), "surprise": 1})
    assert fake.requests == []


def test_identity_arguments_are_never_accepted():
    fake = Fake()
    srv = server(fake)
    for name in sorted(READS | WRITES):
        for key, value in IDENTITY.items():
            with pytest.raises(Exception, match="invalid_arguments"):
                call(srv, name, {**ARGS.get(name, {}), key: value})
    assert fake.requests == []
    for name in READS | WRITES:
        tool = next(t for t in asyncio.run(srv.list_tools()) if t.name == name)
        assert not set(IDENTITY) & set(tool.input_schema["properties"])


def test_every_call_carries_the_callers_bearer_and_nothing_else_of_identity():
    fake = Fake()
    srv = server(fake)
    for name in sorted(READS | WRITES):
        call(srv, name, ARGS.get(name, {}))
    assert len(fake.requests) == len(READS | WRITES)
    for request in fake.requests:
        assert request.headers["authorization"] == "Bearer tok-123"
        assert "tok-123" not in str(request.url)
        assert request.url.host == "api.test"


def test_sample_calls_map_to_the_api():
    for name, args, method, path, params in SAMPLES:
        fake = Fake()
        call(server(fake), name, args)
        request = fake.requests[-1]
        assert (request.method, request.url.path) == (method, path), name
        assert dict(request.url.params) == params, name


def test_errors_carry_only_the_status_and_a_short_code():
    fake = Fake(status=403, body={"detail": {"error": "forbidden", "secret": "tok-123 do-not-leak"}})
    with pytest.raises(Exception) as caught:
        call(server(fake), sorted(READS)[0], ARGS.get(sorted(READS)[0], {}))
    assert str(caught.value).endswith("403: forbidden") and "do-not-leak" not in str(caught.value)


def test_transport_failure_does_not_echo_the_error():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Authorization: Bearer tok-123 refused")
    srv = build_server(httpx.Client(transport=httpx.MockTransport(boom), base_url="https://api.test"),
                       lambda: "tok-123").server
    with pytest.raises(Exception) as caught:
        call(srv, sorted(READS)[0], ARGS.get(sorted(READS)[0], {}))
    assert "tok-123" not in str(caught.value) and "503" in str(caught.value)


def test_url_must_be_https_or_loopback(tmp_path):
    assert mod.api_url(API_KEY, {API_KEY: "https://x.example"}) == "https://x.example"
    assert mod.api_url(API_KEY, {API_KEY: "http://127.0.0.1:9"}) == "http://127.0.0.1:9"
    with pytest.raises(mod.ConfigError):
        mod.api_url(API_KEY, {API_KEY: "http://example.com"})
    with pytest.raises(mod.ConfigError):
        mod.api_url(API_KEY, {"EMPIRE_CLIENT_CONFIG": str(tmp_path / "none")})


def test_token_order_and_file_mode(tmp_path):
    token_file = tmp_path / "t.jwt"
    token_file.write_text("from-file\n")
    token_file.chmod(0o644)
    with pytest.raises(mod.ConfigError):
        mod.bearer({"EMPIRE_TOKEN_FILE": str(token_file)})
    token_file.chmod(0o600)
    assert mod.bearer({"EMPIRE_TOKEN_FILE": str(token_file)}) == "from-file"
    assert mod.bearer({"EMPIRE_TOKEN": "env", "EMPIRE_TOKEN_FILE": str(token_file)}) == "env"
    assert mod.bearer({"EMPIRE_MCP_AUTOMATION": "x-y", "EMPIRE_AUTOMATION_TOKEN_X_Y": "auto"}) == "auto"
