from __future__ import annotations

import getpass
import json
import os
from collections.abc import Iterable
from typing import Any

import requests


BASE_URL = "https://api.zenginehq.com/v1"
FORM_ID = int(os.getenv("ZENGINE_FORM_ID", "185672"))


def main() -> int:
    token = os.getenv("ZENGINE_API_TOKEN") or getpass.getpass("Zengine API token: ")
    try:
        form = get_json(f"{BASE_URL}/forms/{FORM_ID}.json", token)
        records = get_json(
            f"{BASE_URL}/forms/{FORM_ID}/records",
            token,
            {"limit": 5, "page": 1, "sort": "modified", "direction": "desc"},
        )
    except requests.RequestException as exc:
        print(f"Could not reach Zengine or the token was rejected: {safe_error(exc, token)}")
        return 1

    print(f"Form {FORM_ID}")
    print("")
    print("Likely field IDs:")
    for field in extract_fields(form):
        label = str(field.get("label") or field.get("name") or field.get("title") or "")
        field_id = display_field_id(field)
        if not label and not field_id:
            continue
        lower = label.lower()
        if any(term in lower for term in ("status", "memo", "description", "amount", "payee")):
            print(f"- {field_id}: {label}")

    print("")
    print("All field labels:")
    all_fields = extract_fields(form)
    for field in all_fields:
        label = str(field.get("label") or field.get("name") or field.get("title") or "")
        field_id = display_field_id(field)
        if label or field_id:
            print(f"- {field_id}: {label}")
    if not all_fields:
        print("No field metadata found in the form response.")
        print("Form response shape:")
        print(shape(form))

    print("")
    print("Status/payment memo metadata:")
    for field in all_fields:
        label = str(field.get("label") or field.get("name") or field.get("title") or "")
        if any(term in label.lower() for term in ("status", "payment memo")):
            print(f"- {display_field_id(field)}: {label}")
            print(f"  {compact(field, limit=1200)}")

    print("")
    print("Sample record field values:")
    data = records.get("data", [])
    if isinstance(data, list) and data:
        sample = data[0]
        for key, value in sample.items():
            if key.startswith("field"):
                print(f"- {key}: {compact(value)}")
    else:
        print("No sample records returned.")

    return 0


def get_json(url: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    request_params = dict(params or {})
    request_params["access_token"] = token
    response = requests.get(url, params=request_params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected JSON response")
    return payload


def extract_fields(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("fields"), list):
            return [field for field in data["fields"] if isinstance(field, dict)]
    fields: list[dict[str, Any]] = []
    walk(payload, fields)
    return fields


def walk(value: Any, fields: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if looks_like_field(value):
            fields.append(value)
        for child in value.values():
            walk(child, fields)
    elif isinstance(value, list):
        for child in value:
            walk(child, fields)


def looks_like_field(value: dict[str, Any]) -> bool:
    keys = set(value)
    has_label = bool(keys & {"label", "name", "title"})
    has_id = any(value.get(key) for key in ("id", "key", "fieldId", "apiKey"))
    return has_label and has_id


def compact(value: Any, limit: int = 180) -> str:
    text = json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
    return text[:limit]


def safe_error(exc: Exception, token: str) -> str:
    return str(exc).replace(token, "[REDACTED]")


def display_field_id(field: dict[str, Any]) -> str:
    raw = str(field.get("apiKey") or field.get("key") or field.get("fieldId") or field.get("id") or "")
    if raw.isdigit():
        return f"field{raw}"
    return raw


def shape(value: Any, depth: int = 0) -> str:
    if depth >= 3:
        return type(value).__name__
    if isinstance(value, dict):
        shaped = {}
        for key, child in list(value.items())[:20]:
            shaped[key] = shape(child, depth + 1)
        return json.dumps(shaped, indent=2)
    if isinstance(value, list):
        if not value:
            return "empty list"
        return f"list[{shape(value[0], depth + 1)}]"
    return type(value).__name__


if __name__ == "__main__":
    raise SystemExit(main())
