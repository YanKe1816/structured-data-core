import asyncio
import json
import re
import time

from fastapi.testclient import TestClient

from app.main import app, sse
from app.mcp import MCP_MANIFEST, TOOL_DEFINITIONS

client = TestClient(app)


def rpc(method: str, params: dict, req_id: int = 1):
    return client.post(
        "/message",
        json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": params},
    )


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_privacy_terms_support_exist():
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200
    assert client.get("/support").status_code == 200


def test_mcp_manifest_consistent_with_tools_list():
    manifest = client.get("/mcp").json()
    assert manifest["name"] == "structured-data-core"
    assert manifest["base_url"] == "/"

    list_response = rpc("tools/list", {})
    list_tools = list_response.json()["result"]["tools"]
    manifest_tools = manifest["tools"]

    assert [item["name"] for item in list_tools] == [
        "data_validate",
        "data_normalize",
        "data_fill_defaults",
        "data_map_fields",
        "data_pick_fields",
    ]
    assert manifest_tools == list_tools

    for tool in list_tools:
        assert tool["readOnlyHint"] is True
        assert tool["openWorldHint"] is False
        assert tool["destructiveHint"] is False


def test_platform_freeze_canonical_metadata_source():
    assert MCP_MANIFEST["tools"] is TOOL_DEFINITIONS

    list_response = rpc("tools/list", {})
    list_tools = list_response.json()["result"]["tools"]

    assert list_tools == TOOL_DEFINITIONS


def test_source_contains_required_platform_routes():
    source = __import__("pathlib").Path("app/main.py").read_text()
    assert '@app.get("/mcp")' in source
    assert '@app.get("/terms")' in source


def test_data_validate():
    response = rpc(
        "tools/call",
        {
            "name": "data_validate",
            "arguments": {
                "rules": {
                    "required": ["a", "b"],
                    "type": {"a": "string", "b": "integer"},
                    "enum": {"status": ["new", "ok", "bad"]},
                },
                "data": {"a": "x", "b": 2, "status": "ok"},
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["result"] == {"ok": True, "issues": []}


def test_data_normalize():
    response = rpc(
        "tools/call",
        {
            "name": "data_normalize",
            "arguments": {
                "data": {"name": "  Alice   Smith  ", "meta": {"city": "  New   York"}},
                "options": {
                    "trim_strings": True,
                    "collapse_spaces": True,
                    "remove_empty_strings": False,
                },
            },
        },
    )
    result = response.json()["result"]
    assert result["data"] == {"name": "Alice Smith", "meta": {"city": "New York"}}
    assert len(result["changes"]) == 2


def test_data_fill_defaults():
    response = rpc(
        "tools/call",
        {
            "name": "data_fill_defaults",
            "arguments": {
                "data": {"a": 1, "b": None},
                "defaults": {"b": 2, "c": 3},
            },
        },
    )
    assert response.json()["result"] == {"data": {"a": 1, "b": 2, "c": 3}, "filled": ["b", "c"]}


def test_data_map_fields():
    response = rpc(
        "tools/call",
        {
            "name": "data_map_fields",
            "arguments": {
                "data": {"oldField": 1, "a": {"b": "x"}},
                "mapping": {"oldField": "newField", "a.b": "c.d"},
            },
        },
    )
    result = response.json()["result"]
    assert result["data"] == {"a": {}, "newField": 1, "c": {"d": "x"}}
    assert result["moved"] == [{"from": "oldField", "to": "newField"}, {"from": "a.b", "to": "c.d"}]


def test_data_pick_fields():
    response = rpc(
        "tools/call",
        {
            "name": "data_pick_fields",
            "arguments": {
                "data": {"a": 1, "b": 2, "c": {"d": 3, "e": 4}},
                "fields": ["a", "c.d", "missing"],
            },
        },
    )
    assert response.json()["result"] == {"data": {"a": 1, "c": {"d": 3}}, "picked": ["a", "c.d"]}


def test_invalid_params_error_contract():
    response = rpc(
        "tools/call",
        {
            "name": "data_fill_defaults",
            "arguments": {"data": []},
        },
    )
    error = response.json()["error"]
    assert error["code"] == -32602
    assert error["message"] == "Invalid params"
    assert "issues" in error["data"]


def test_tools_call_accepts_session_id_parameter():
    response = rpc(
        "tools/call",
        {
            "sessionId": "session-1",
            "name": "data_pick_fields",
            "arguments": {
                "data": {"a": 1, "b": 2},
                "fields": ["a"],
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["result"] == {"data": {"a": 1}, "picked": ["a"]}


def test_sse_headers_and_first_event_under_one_second_and_uuid():
    start = time.monotonic()
    response = client.get("/sse")
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 1.0
    assert response.headers["content-type"] == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
    assert response.text.startswith("event: connected\n")

    lines = response.text.strip().splitlines()
    assert lines[0] == "event: connected"
    assert lines[1].startswith("data: ")
    payload = json.loads(lines[1].replace("data: ", "", 1))
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        payload["session_id"],
    )


def test_sse_ping_interval_and_payload(monkeypatch):
    calls: list[float] = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr("app.main.asyncio.sleep", fake_sleep)

    async def run_stream_once():
        response = await sse()
        assert response.media_type == "text/event-stream"
        first = await response.stream.__anext__()
        second = await response.stream.__anext__()
        return first, second

    first, second = asyncio.run(run_stream_once())
    assert first.startswith("event: connected\n")
    assert second == ": ping\n\n"
    assert calls and calls[0] == 15
