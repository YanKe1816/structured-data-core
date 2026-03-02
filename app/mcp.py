from __future__ import annotations

from typing import Any, Callable

from app.tools.fill_defaults import fill_defaults, validate_input_issues as fill_issues
from app.tools.map_fields import map_fields, validate_input_issues as map_issues
from app.tools.normalize import normalize_data, validate_input_issues as normalize_issues
from app.tools.pick_fields import pick_fields, validate_input_issues as pick_issues
from app.tools.validate import validate_data, validate_input_issues as validate_issues

JSON = dict[str, Any]


TOOLS: dict[str, tuple[Callable[[JSON], JSON], Callable[[Any], list[dict[str, str]]]]] = {
    "data_validate": (validate_data, validate_issues),
    "data_normalize": (normalize_data, normalize_issues),
    "data_fill_defaults": (fill_defaults, fill_issues),
    "data_map_fields": (map_fields, map_issues),
    "data_pick_fields": (pick_fields, pick_issues),
}


TOOL_DEFINITIONS: list[JSON] = [
    {
        "name": "data_validate",
        "description": "Validate data against required/type/enum rules.",
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
    {
        "name": "data_normalize",
        "description": "Normalize string values and track deterministic changes.",
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
    {
        "name": "data_fill_defaults",
        "description": "Fill missing or null top-level fields with provided defaults.",
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
    {
        "name": "data_map_fields",
        "description": "Move values across object fields using dot-path mapping.",
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
    {
        "name": "data_pick_fields",
        "description": "Select only requested fields using dot paths.",
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
]


MCP_MANIFEST: JSON = {
    "name": "structured-data-core",
    "version": "1.0.0",
    "protocol": "json-rpc-2.0",
    "base_url": "/",
    "endpoints": {"message": "/message", "sse": "/sse"},
    "tools": TOOL_DEFINITIONS,
}


def _error_response(request_id: Any, code: int, message: str, issues: list[dict[str, str]] | None = None) -> JSON:
    error: JSON = {"code": code, "message": message}
    if issues is not None:
        error["data"] = {"issues": issues}
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def handle_rpc(body: Any) -> JSON | None:
    if not isinstance(body, dict):
        return _error_response(None, -32600, "Invalid Request")

    request_id = body.get("id")
    jsonrpc = body.get("jsonrpc")
    method = body.get("method")
    params = body.get("params", {})

    if jsonrpc != "2.0" or not isinstance(method, str):
        return _error_response(request_id, -32600, "Invalid Request")

    if method == "notifications/initialized":
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": {"ok": True}}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "serverInfo": {"name": MCP_MANIFEST["name"], "version": MCP_MANIFEST["version"]},
                "capabilities": {"tools": {"listChanged": False}},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOL_DEFINITIONS}}

    if method == "tools/call":
        if not isinstance(params, dict):
            return _error_response(request_id, -32602, "Invalid params", [{"path": "params", "code": "type", "message": "params must be an object"}])

        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in TOOLS:
            return _error_response(request_id, -32602, "Invalid params", [{"path": "name", "code": "unknown", "message": "unknown tool"}])

        tool_fn, validation_fn = TOOLS[name]
        issues = validation_fn(arguments)
        if issues:
            return _error_response(request_id, -32602, "Invalid params", issues)

        try:
            result = tool_fn(arguments)
        except Exception:
            return _error_response(request_id, -32000, "Internal error")

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    return _error_response(request_id, -32601, "Method not found")
