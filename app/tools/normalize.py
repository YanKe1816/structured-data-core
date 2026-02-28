from __future__ import annotations

from copy import deepcopy
from typing import Any


def _normalize_object(
    obj: Any,
    options: dict[str, bool],
    changes: list[dict[str, Any]],
    path: str = "",
) -> Any:
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else key
            normalized = _normalize_object(value, options, changes, child_path)
            if options.get("remove_empty_strings", False) and normalized == "":
                changes.append({"path": child_path, "from": value, "to": None})
                continue
            result[key] = normalized
        return result

    if isinstance(obj, list):
        return [
            _normalize_object(item, options, changes, f"{path}.{index}" if path else str(index))
            for index, item in enumerate(obj)
        ]

    if isinstance(obj, str):
        updated = obj
        if options.get("trim_strings", False):
            updated = updated.strip()
        if options.get("collapse_spaces", False):
            updated = " ".join(updated.split())

        if updated != obj:
            changes.append({"path": path, "from": obj, "to": updated})
        return updated

    return obj


def normalize_data(payload: dict[str, Any]) -> dict[str, Any]:
    data_copy = deepcopy(payload["data"])
    options = payload.get("options", {})
    normalized_options = {
        "trim_strings": bool(options.get("trim_strings", True)),
        "collapse_spaces": bool(options.get("collapse_spaces", True)),
        "remove_empty_strings": bool(options.get("remove_empty_strings", False)),
    }
    changes: list[dict[str, Any]] = []
    normalized = _normalize_object(data_copy, normalized_options, changes)
    return {"data": normalized, "changes": changes}


def validate_input_issues(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return [{"path": "", "code": "type", "message": "params must be an object"}]
    issues: list[dict[str, str]] = []
    if "data" not in payload or not isinstance(payload["data"], dict):
        issues.append({"path": "data", "code": "type", "message": "data must be an object"})
    if "options" in payload and not isinstance(payload["options"], dict):
        issues.append({"path": "options", "code": "type", "message": "options must be an object"})
    return issues
