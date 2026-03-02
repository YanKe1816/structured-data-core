import asyncio
import json

from app.main import app


def req(method: str, url: str, payload: dict | None = None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return asyncio.run(app.dispatch(method, url, body))


def rpc(method: str, params: dict, req_id: int = 1, url: str = "/message"):
    response = req("POST", url, {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
    return response.json()


def test_tools_list_and_manifest_consistent():
    mcp = req("GET", "/mcp").json()
    listed = rpc("tools/list", {})["result"]["tools"]
    assert [t["name"] for t in listed] == [
        "data_validate",
        "data_normalize",
        "data_fill_defaults",
        "data_map_fields",
        "data_pick_fields",
    ]
    assert mcp["tools"] == listed


def test_tools_call_each_and_unified_output():
    r1 = rpc("tools/call", {"name": "data_validate", "arguments": {"rules": {"required": ["a"]}, "data": {"a": 1}}})
    assert r1["result"]["success"] is True
    assert set(r1["result"].keys()) == {"success", "errors", "data"}

    r2 = rpc("tools/call", {"name": "data_normalize", "arguments": {"data": {"x": "  a   b "}}})
    assert r2["result"]["data"]["data"]["x"] == "a b"

    r3 = rpc("tools/call", {"name": "data_fill_defaults", "arguments": {"data": {"a": None}, "defaults": {"a": 1, "b": 2}}})
    assert r3["result"]["data"]["data"] == {"a": 1, "b": 2}

    r4 = rpc("tools/call", {"name": "data_map_fields", "arguments": {"data": {"a": {"b": 1}}, "mapping": {"a.b": "c.d"}}})
    assert r4["result"]["data"]["data"]["c"]["d"] == 1

    r5 = rpc("tools/call", {"name": "data_pick_fields", "arguments": {"data": {"a": 1, "b": {"c": 2}}, "fields": ["b.c"]}})
    assert r5["result"]["data"]["data"] == {"b": {"c": 2}}


def test_message_accepts_session_query_parameter():
    r = rpc(
        "tools/call",
        {"name": "data_pick_fields", "arguments": {"data": {"a": 1}, "fields": ["a"]}},
        url="/message?sessionId=session-abc",
    )
    assert r["result"]["success"] is True
