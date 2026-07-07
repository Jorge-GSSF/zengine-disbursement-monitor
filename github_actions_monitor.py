from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from zengine_auth import get_zengine_api_token


ZENGINE_API_BASE_URL = "https://api.zenginehq.com/v1"
ZENGINE_FORM_ID = int(os.getenv("ZENGINE_FORM_ID", "185672"))
STATUS_FIELD_ID = os.getenv("ZENGINE_STATUS_FIELD_ID", "field3589680")
APPROVED_VALUE = os.getenv("ZENGINE_APPROVED_VALUE", "Approved")
AMOUNT_FIELD_ID = os.getenv("ZENGINE_AMOUNT_FIELD_ID", "field3583325")
PAYMENT_MEMO_FIELD_ID = os.getenv("ZENGINE_PAYMENT_MEMO_FIELD_ID", "field6995603")
LINKED_PAYEE_FIELD_ID = os.getenv("ZENGINE_LINKED_PAYEE_FIELD_ID", "field3588097")
SORT_FIELD = os.getenv("ZENGINE_SORT_FIELD", "modified")
MAX_PAGES = int(os.getenv("ZENGINE_MAX_PAGES", "20"))
STATE_PATH = Path(os.getenv("MONITOR_STATE_PATH", "state/notified_records.json"))


def main() -> int:
    zengine_token = resolve_zengine_token()
    telegram_token = required_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = required_env("TELEGRAM_CHAT_ID")

    print("Loading monitor state...")
    state = load_state()
    already_notified = set(str(value) for value in state.get("notified_record_ids", []))
    initialized = bool(state.get("initialized", False))

    print("Fetching Zengine records...")
    records = fetch_records(zengine_token)
    approved_records = [record for record in records if is_approved(record)]
    print(f"Fetched {len(records)} records; found {len(approved_records)} approved records.")

    sent = 0
    added_ids: set[str] = set()
    for record in approved_records:
        record_id = str(record.get("id") or "").strip()
        if not record_id or record_id in already_notified:
            continue

        if initialized:
            print(f"Sending Telegram notification for Zengine record {record_id}...")
            send_telegram_message(telegram_token, telegram_chat_id, build_message(record))
            sent += 1

        added_ids.add(record_id)

    print("Saving monitor state...")
    next_ids = sorted(already_notified | added_ids)
    save_state(
        {
            "initialized": True,
            "notified_record_ids": next_ids,
        }
    )

    if not initialized:
        print(
            f"Initialized state with {len(approved_records)} existing approved records. "
            "No backlog messages sent."
        )
    else:
        print(
            f"Scanned {len(records)} records; approved={len(approved_records)}; "
            f"new_notifications={sent}; newly_marked={len(added_ids)}."
        )

    return 0


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_zengine_token() -> str:
    token = os.getenv("ZENGINE_API_TOKEN", "").strip()
    if token:
        print("Using Zengine API token from environment.")
        print(f"::add-mask::{token}")
        return token

    email = required_env("ZENGINE_LOGIN_EMAIL")
    password = required_env("ZENGINE_LOGIN_PASSWORD")
    print("No Zengine API token configured; logging into Zengine to retrieve one...")
    token = get_zengine_api_token(email, password)
    print(f"::add-mask::{token}")
    print("Retrieved Zengine API token for this workflow run.")
    return token


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"initialized": False, "notified_record_ids": []}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"initialized": False, "notified_record_ids": []}
    return data if isinstance(data, dict) else {"initialized": False, "notified_record_ids": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_records(token: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        payload = get_json(
            f"{ZENGINE_API_BASE_URL}/forms/{ZENGINE_FORM_ID}/records",
            {
                "access_token": token,
                "limit": "100",
                "page": str(page),
                "sort": SORT_FIELD,
                "direction": "desc",
            },
        )
        page_records = payload.get("data", [])
        if not isinstance(page_records, list) or not page_records:
            break
        records.extend(record for record in page_records if isinstance(record, dict))
        total_count = int(payload.get("totalCount", 0) or 0)
        if total_count and len(records) >= total_count:
            break
        if len(page_records) < 100:
            break
    return records


def get_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected JSON response from {url}")
    return payload


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status >= 400:
                raise RuntimeError(f"Telegram API returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Telegram API returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Telegram API: {exc.reason}") from exc


def is_approved(record: dict[str, Any]) -> bool:
    return clean_text(record.get(STATUS_FIELD_ID)).casefold() == APPROVED_VALUE.casefold()


def build_message(record: dict[str, Any]) -> str:
    amount = format_amount(record.get(AMOUNT_FIELD_ID))
    memo = clean_text(record.get(PAYMENT_MEMO_FIELD_ID)) or "No memo"
    payee = display_value(record.get(LINKED_PAYEE_FIELD_ID)) or "Unknown payee"
    return f"New Disbursement Allocation added: {amount} - {memo} - {payee}"


def display_value(value: Any) -> str:
    if isinstance(value, dict):
        return clean_text(value.get("name") or value.get("displayName") or value.get("value"))
    if isinstance(value, list):
        return ", ".join(filter(None, (display_value(item) for item in value)))
    return clean_text(value)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return display_value(value)
    return str(value).strip()


def format_amount(value: Any) -> str:
    if value in (None, ""):
        return "$0.00"
    try:
        return f"${float(str(value).replace(',', '').replace('$', '')):,.2f}"
    except ValueError:
        text = str(value).strip()
        return text if text.startswith("$") else f"${text}"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        raise SystemExit(1)
