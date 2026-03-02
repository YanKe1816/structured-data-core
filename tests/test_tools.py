from fastapi.testclient import TestClient

from app.main import app
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


def test_sse_headers_and_initial_event_line():
    response = client.get("/sse")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.text.startswith(":ok\n\n")
