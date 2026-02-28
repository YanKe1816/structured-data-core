from __future__ import annotations

from copy import deepcopy
from typing import Any


_MISSING = object()


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _delete_path(data: dict[str, Any], path: str) -> None:
    parts = path.split(".")
    current: Any = data
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current: Any = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def map_fields(payload: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(payload["data"])
    mapping = payload["mapping"]
    moved: list[dict[str, str]] = []

    for source, destination in mapping.items():
        value = _get_path(data, source)
        if value is _MISSING:
            continue
        _set_path(data, destination, value)
        _delete_path(data, source)
        moved.append({"from": source, "to": destination})

    return {"data": data, "moved": moved}


def validate_input_issues(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return [{"path": "", "code": "type", "message": "params must be an object"}]
    issues: list[dict[str, str]] = []
    if "data" not in payload or not isinstance(payload["data"], dict):
        issues.append({"path": "data", "code": "type", "message": "data must be an object"})
    if "mapping" not in payload or not isinstance(payload["mapping"], dict):
        issues.append({"path": "mapping", "code": "type", "message": "mapping must be an object"})
    elif not all(isinstance(k, str) and isinstance(v, str) for k, v in payload["mapping"].items()):
        issues.append({"path": "mapping", "code": "type", "message": "mapping keys and values must be strings"})
    return issues
