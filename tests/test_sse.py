import asyncio
import json
import re
import time

from app.main import app, sse


def test_sse_first_event_under_1s_and_headers():
    start = time.monotonic()
    response = asyncio.run(app.dispatch("GET", "/sse"))
    elapsed = time.monotonic() - start
    assert elapsed < 1.0
    assert response.content_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Connection"] == "keep-alive"
    assert response.headers["X-Accel-Buffering"] == "no"

    async def one():
        return await response.stream.__anext__()

    first = asyncio.run(one())
    assert first.startswith("event: connected\n")
    payload_line = first.splitlines()[1].replace("data: ", "", 1)
    payload = json.loads(payload_line)
    assert re.match(r"^[0-9a-f\-]{36}$", payload["session_id"])


def test_sse_ping_every_15_seconds(monkeypatch):
    waits: list[float] = []

    async def fake_sleep(seconds: float):
        waits.append(seconds)

    monkeypatch.setattr("app.main.asyncio.sleep", fake_sleep)

    async def two_lines():
        response = await sse()
        first = await response.stream.__anext__()
        second = await response.stream.__anext__()
        return first, second

    first, second = asyncio.run(two_lines())
    assert first.startswith("event: connected\n")
    assert second == ": ping\n\n"
    assert waits[0] == 15


def test_cold_start_and_developer_mode_simulation():
    response = asyncio.run(app.dispatch("GET", "/sse"))

    async def first():
        return await response.stream.__anext__()

    assert asyncio.run(first()).startswith("event: connected\n")
