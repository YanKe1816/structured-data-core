from __future__ import annotations

from copy import deepcopy
from typing import Any


def fill_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(payload["data"])
    defaults = payload["defaults"]
    filled: list[str] = []

    for key, value in defaults.items():
        if key not in data or data[key] is None:
            data[key] = deepcopy(value)
            filled.append(key)

    return {"data": data, "filled": filled}


def validate_input_issues(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return [{"path": "", "code": "type", "message": "params must be an object"}]
    issues: list[dict[str, str]] = []
    if "data" not in payload or not isinstance(payload["data"], dict):
        issues.append({"path": "data", "code": "type", "message": "data must be an object"})
    if "defaults" not in payload or not isinstance(payload["defaults"], dict):
        issues.append({"path": "defaults", "code": "type", "message": "defaults must be an object"})
    return issues
