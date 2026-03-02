from __future__ import annotations

from copy import deepcopy
from typing import Any

JSON = dict[str, Any]

TOOL_DEFINITIONS: list[JSON] = [
    {"name": "data_validate", "readOnlyHint": True, "openWorldHint": False, "destructiveHint": False},
    {"name": "data_normalize", "readOnlyHint": True, "openWorldHint": False, "destructiveHint": False},
    {"name": "data_fill_defaults", "readOnlyHint": True, "openWorldHint": False, "destructiveHint": False},
    {"name": "data_map_fields", "readOnlyHint": True, "openWorldHint": False, "destructiveHint": False},
    {"name": "data_pick_fields", "readOnlyHint": True, "openWorldHint": False, "destructiveHint": False},
]

MCP_MANIFEST: JSON = {
    "name": "structured-data-core",
    "version": "1.0.0",
    "protocol": "jsonrpc-2.0",
    "base_url": "/",
    "endpoints": {"message": "/message", "sse": "/sse"},
    "tools": TOOL_DEFINITIONS,
}

_ALLOWED_TYPES = {"string", "number", "integer", "boolean", "object", "array"}
_MISSING = object()


def _ok(data: Any) -> JSON:
    return {"success": True, "errors": [], "data": data}


def _fail(errors: list[JSON]) -> JSON:
    return {"success": False, "errors": errors, "data": None}


def _type_match(v: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(v, str)
    if expected == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if expected == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if expected == "boolean":
        return isinstance(v, bool)
    if expected == "object":
        return isinstance(v, dict)
    if expected == "array":
        return isinstance(v, list)
    return False


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    current: Any = data
    parts = path.split(".")
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _del_path(data: dict[str, Any], path: str) -> None:
    current: Any = data
    parts = path.split(".")
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


def _tool_validate(arguments: Any) -> JSON:
    if not isinstance(arguments, dict):
        return _fail([{"path": "", "code": "type", "message": "arguments must be object"}])
    rules = arguments.get("rules")
    data = arguments.get("data")
    if not isinstance(rules, dict) or not isinstance(data, dict):
        return _fail([{"path": "rules|data", "code": "type", "message": "rules and data must be object"}])

    issues: list[JSON] = []
    for key in rules.get("required", []):
        if key not in data:
            issues.append({"path": key, "code": "missing", "message": f"{key} is required"})

    type_rules = rules.get("type", {})
    if isinstance(type_rules, dict):
        for key, expected in type_rules.items():
            if expected in _ALLOWED_TYPES and key in data and not _type_match(data[key], expected):
                issues.append({"path": key, "code": "type", "message": f"{key} must be {expected}"})

    enum_rules = rules.get("enum", {})
    if isinstance(enum_rules, dict):
        for key, allowed in enum_rules.items():
            if key in data and isinstance(allowed, list) and data[key] not in allowed:
                issues.append({"path": key, "code": "enum", "message": f"{key} must be one of {allowed}"})

    return _ok({"ok": len(issues) == 0, "issues": issues})


def _normalize_walk(obj: Any, options: dict[str, bool], changes: list[JSON], path: str = "") -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            nv = _normalize_walk(v, options, changes, p)
            if options["remove_empty_strings"] and nv == "":
                changes.append({"path": p, "from": v, "to": None})
                continue
            out[k] = nv
        return out
    if isinstance(obj, list):
        return [_normalize_walk(v, options, changes, f"{path}.{i}" if path else str(i)) for i, v in enumerate(obj)]
    if isinstance(obj, str):
        nv = obj.strip() if options["trim_strings"] else obj
        if options["collapse_spaces"]:
            nv = " ".join(nv.split())
        if nv != obj:
            changes.append({"path": path, "from": obj, "to": nv})
        return nv
    return obj


def _tool_normalize(arguments: Any) -> JSON:
    if not isinstance(arguments, dict) or not isinstance(arguments.get("data"), dict):
        return _fail([{"path": "data", "code": "type", "message": "data must be object"}])
    opts = arguments.get("options", {}) if isinstance(arguments.get("options", {}), dict) else {}
    options = {
        "trim_strings": bool(opts.get("trim_strings", True)),
        "collapse_spaces": bool(opts.get("collapse_spaces", True)),
        "remove_empty_strings": bool(opts.get("remove_empty_strings", False)),
    }
    changes: list[JSON] = []
    out = _normalize_walk(deepcopy(arguments["data"]), options, changes)
    return _ok({"data": out, "changes": changes})


def _tool_fill_defaults(arguments: Any) -> JSON:
    if not isinstance(arguments, dict) or not isinstance(arguments.get("data"), dict) or not isinstance(arguments.get("defaults"), dict):
        return _fail([{"path": "data|defaults", "code": "type", "message": "data/defaults must be object"}])
    data = deepcopy(arguments["data"])
    defaults = arguments["defaults"]
    filled: list[str] = []
    for k, v in defaults.items():
        if k not in data or data[k] is None:
            data[k] = deepcopy(v)
            filled.append(k)
    return _ok({"data": data, "filled": filled})


def _tool_map_fields(arguments: Any) -> JSON:
    if not isinstance(arguments, dict) or not isinstance(arguments.get("data"), dict) or not isinstance(arguments.get("mapping"), dict):
        return _fail([{"path": "data|mapping", "code": "type", "message": "data/mapping must be object"}])
    data = deepcopy(arguments["data"])
    moved: list[JSON] = []
    for src, dst in arguments["mapping"].items():
        if not isinstance(src, str) or not isinstance(dst, str):
            continue
        value = _get_path(data, src)
        if value is _MISSING:
            continue
        _set_path(data, dst, value)
        _del_path(data, src)
        moved.append({"from": src, "to": dst})
    return _ok({"data": data, "moved": moved})


def _tool_pick_fields(arguments: Any) -> JSON:
    if not isinstance(arguments, dict) or not isinstance(arguments.get("data"), dict) or not isinstance(arguments.get("fields"), list):
        return _fail([{"path": "data|fields", "code": "type", "message": "data must be object and fields array"}])
    out: dict[str, Any] = {}
    picked: list[str] = []
    for field in arguments["fields"]:
        if not isinstance(field, str):
            continue
        value = _get_path(arguments["data"], field)
        if value is _MISSING:
            continue
        _set_path(out, field, deepcopy(value))
        picked.append(field)
    return _ok({"data": out, "picked": picked})


_TOOL_CALLS = {
    "data_validate": _tool_validate,
    "data_normalize": _tool_normalize,
    "data_fill_defaults": _tool_fill_defaults,
    "data_map_fields": _tool_map_fields,
    "data_pick_fields": _tool_pick_fields,
}


def _rpc_error(request_id: Any, code: int, message: str, data: Any | None = None) -> JSON:
    error: JSON = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def handle_rpc(body: Any, session_id: str | None = None) -> JSON | None:
    if not isinstance(body, dict):
        return _rpc_error(None, -32600, "Invalid Request")

    request_id = body.get("id")
    if body.get("jsonrpc") != "2.0" or not isinstance(body.get("method"), str):
        return _rpc_error(request_id, -32600, "Invalid Request")

    method = body["method"]
    params = body.get("params", {})
    if not isinstance(params, dict):
        return _rpc_error(request_id, -32602, "Invalid params")

    if session_id and "sessionId" not in params:
        params = {**params, "sessionId": session_id}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"serverInfo": {"name": "structured-data-core", "version": "1.0.0"}, "capabilities": {"tools": {"listChanged": False}}},
        }
    if method == "notifications/initialized":
        return None if request_id is None else {"jsonrpc": "2.0", "id": request_id, "result": {"ok": True}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOL_DEFINITIONS}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in _TOOL_CALLS:
            return _rpc_error(request_id, -32602, "Invalid params", {"issues": [{"path": "name", "code": "unknown", "message": "unknown tool"}]})
        result = _TOOL_CALLS[name](arguments)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    return _rpc_error(request_id, -32601, "Method not found")
