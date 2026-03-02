from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.tools.map_fields import _MISSING, _get_path, _set_path


def pick_fields(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload["data"]
    fields: list[str] = payload["fields"]
    output: dict[str, Any] = {}
    picked: list[str] = []

    for field in fields:
        value = _get_path(data, field)
        if value is _MISSING:
            continue
        _set_path(output, field, deepcopy(value))
        picked.append(field)

    return {"data": output, "picked": picked}


def validate_input_issues(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return [{"path": "", "code": "type", "message": "params must be an object"}]
    issues: list[dict[str, str]] = []
    if "data" not in payload or not isinstance(payload["data"], dict):
        issues.append({"path": "data", "code": "type", "message": "data must be an object"})
    if "fields" not in payload or not isinstance(payload["fields"], list):
        issues.append({"path": "fields", "code": "type", "message": "fields must be an array"})
    elif not all(isinstance(f, str) for f in payload["fields"]):
        issues.append({"path": "fields", "code": "type", "message": "fields must contain strings"})
    return issues
