from __future__ import annotations

from typing import Any

_ALLOWED_TYPES = {"string", "number", "integer", "boolean", "object", "array"}


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return False


def validate_data(payload: dict[str, Any]) -> dict[str, Any]:
    rules = payload.get("rules", {})
    data = payload.get("data", {})
    issues: list[dict[str, str]] = []

    required = rules.get("required", [])
    for key in required:
        if key not in data:
            issues.append({"path": key, "code": "missing", "message": f"{key} is required"})

    type_rules = rules.get("type", {})
    for key, expected in type_rules.items():
        if key in data and not _matches_type(data[key], expected):
            issues.append(
                {
                    "path": key,
                    "code": "type",
                    "message": f"{key} must be {expected}",
                }
            )

    enum_rules = rules.get("enum", {})
    for key, values in enum_rules.items():
        if key in data and data[key] not in values:
            issues.append(
                {
                    "path": key,
                    "code": "enum",
                    "message": f"{key} must be one of {values}",
                }
            )

    return {"ok": len(issues) == 0, "issues": issues}


def validate_input_issues(payload: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        return [{"path": "", "code": "type", "message": "params must be an object"}]

    if "rules" not in payload or not isinstance(payload["rules"], dict):
        issues.append({"path": "rules", "code": "type", "message": "rules must be an object"})
    if "data" not in payload or not isinstance(payload["data"], dict):
        issues.append({"path": "data", "code": "type", "message": "data must be an object"})

    if issues:
        return issues

    rules = payload["rules"]
    if "required" in rules:
        required = rules["required"]
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            issues.append(
                {"path": "rules.required", "code": "type", "message": "required must be string array"}
            )

    if "type" in rules:
        type_rules = rules["type"]
        if not isinstance(type_rules, dict):
            issues.append({"path": "rules.type", "code": "type", "message": "type must be an object"})
        else:
            for key, expected in type_rules.items():
                if not isinstance(key, str) or expected not in _ALLOWED_TYPES:
                    issues.append(
                        {
                            "path": f"rules.type.{key}",
                            "code": "type",
                            "message": "invalid type rule",
                        }
                    )

    if "enum" in rules:
        enum_rules = rules["enum"]
        if not isinstance(enum_rules, dict):
            issues.append({"path": "rules.enum", "code": "type", "message": "enum must be an object"})
        else:
            for key, values in enum_rules.items():
                if not isinstance(values, list):
                    issues.append(
                        {
                            "path": f"rules.enum.{key}",
                            "code": "type",
                            "message": "enum values must be an array",
                        }
                    )

    return issues
