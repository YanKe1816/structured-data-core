# ACCEPTANCE

This repository satisfies the commanded production acceptance checks:

1. `python -m compileall app`
2. `pytest -q`
3. Start server and verify `/health` returns `{"status":"ok"}`
4. `/mcp` and `tools/list` are consistent with exactly five tools
5. `/privacy`, `/terms`, `/support` exist
6. `tools/call` works for all five tools

See `DELIVERY_REPORT.md` for run logs and outputs.
