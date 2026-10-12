# Agent Instructions

- Human-facing replies are in Thai by default; keep code, commands and identifiers as-is.
- Never print, commit or copy secrets: database URLs, tokens and keys live in Railway
  variables and `~/.config/solo-habits/` (owner-only).
- Tests use a throwaway local PostgreSQL and a fake platform; they must never reach
  the hosted database or the hosted platform.
- Run `.venv/bin/pytest -q` before committing. Migrations are append-only: never edit
  an applied file, add a new numbered one.
- Deploys are manual (`railway up`) and change production; verify `/health` and one
  authorized read afterwards.
- Keep the solo-empire registry entry (`habits` in
  `repository-catalog/registries/online-systems.yaml`) in sync.
- `habits-mcp` (mcp_server.py in the package) is this cell's MCP server: HTTP API only, caller's own token, no identity arguments; keep tools in step with the API routes and run `tests/test_mcp.py`.
