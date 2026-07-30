from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from settings import Settings
from storage import Storage
from telegram_client import TelegramClient
from zengine import ZengineClient
from zengine_auth import get_zengine_api_token


LOGGER = logging.getLogger(__name__)
INITIALIZED_KEY = "initial_approved_records_loaded"


@dataclass(frozen=True)
class MonitorResult:
    scanned: int
    approved: int
    sent: int
    skipped_existing: int


class DisbursementMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.storage = Storage(settings.database_url)
        self.zengine = ZengineClient(
            self._resolve_zengine_api_token(),
            base_url=settings.zengine_api_base_url,
        )
        self.telegram = TelegramClient(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
        )

    def _resolve_zengine_api_token(self) -> str:
        if self.settings.zengine_api_token:
            return self.settings.zengine_api_token
        if self.settings.zengine_login_email and self.settings.zengine_login_password:
            LOGGER.info("Retrieving Zengine API token from developer page login.")
            return get_zengine_api_token(
                self.settings.zengine_login_email,
                self.settings.zengine_login_password,
            )
        return ""

    def run_once(self) -> MonitorResult:
        missing = self.settings.missing_required_values()
        if missing:
            raise RuntimeError(f"Missing required environment values: {', '.join(missing)}")

        self.storage.init()
        initialized = self.storage.get_state(INITIALIZED_KEY) == "true"
        records = self.zengine.iter_records(
            self.settings.zengine_form_id,
            max_pages=self.settings.zengine_max_pages,
            sort=self.settings.zengine_sort_field,
        )

        approved_records = [record for record in records if self._is_approved(record)]
        sent = 0
        skipped_existing = 0

        for record in approved_records:
            record_id = str(record.get("id") or "").strip()
            if not record_id:
                continue
            status_value = _clean_text(record.get(self.settings.zengine_status_field_id))

            if self.storage.has_notified(record_id):
                skipped_existing += 1
                continue

            if not initialized and not self.settings.notify_existing_on_first_run:
                self.storage.mark_notified(record_id, status_value)
                skipped_existing += 1
                continue

            self.telegram.send_message(self._build_message(record))
            self.storage.mark_notified(record_id, status_value)
            sent += 1

        if not initialized:
            self.storage.set_state(INITIALIZED_KEY, "true")

        result = MonitorResult(
            scanned=len(records),
            approved=len(approved_records),
            sent=sent,
            skipped_existing=skipped_existing,
        )
        LOGGER.info("Monitor result: %s", result)
        return result

    def _is_approved(self, record: dict[str, Any]) -> bool:
        status = _clean_text(record.get(self.settings.zengine_status_field_id))
        return status.casefold() == self.settings.zengine_approved_value.casefold()

    def _build_message(self, record: dict[str, Any]) -> str:
        amount = _format_amount(record.get(self.settings.zengine_amount_field_id))
        payment_type = _clean_text(record.get(self.settings.zengine_payment_type_field_id)) or "Unknown payment type"
        memo = _clean_text(record.get(self.settings.zengine_payment_memo_field_id)) or "No memo"
        payee = _display_value(record.get(self.settings.zengine_linked_payee_field_id)) or "Unknown payee"
        return f"New Disbursement Allocation added: {amount} - {payment_type} - {memo} - {payee}"


def _display_value(value: Any) -> str:
    if isinstance(value, dict):
        return _clean_text(value.get("name") or value.get("displayName") or value.get("value"))
    if isinstance(value, list):
        return ", ".join(filter(None, (_display_value(item) for item in value)))
    return _clean_text(value)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return _display_value(value)
    return str(value).strip()


def _format_amount(value: Any) -> str:
    if value in (None, ""):
        return "$0.00"
    try:
        return f"${float(str(value).replace(',', '').replace('$', '')):,.2f}"
    except ValueError:
        text = str(value).strip()
        return text if text.startswith("$") else f"${text}"
