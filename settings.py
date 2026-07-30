from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        return None


load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    zengine_api_token: str
    zengine_login_email: str = ""
    zengine_login_password: str = ""
    zengine_form_id: int = 185672
    zengine_status_field_id: str = "field3589680"
    zengine_approved_value: str = "Approved"
    zengine_amount_field_id: str = "field3583325"
    zengine_payment_type_field_id: str = "field3609440"
    zengine_payment_memo_field_id: str = "field6995603"
    zengine_linked_payee_field_id: str = "field3588097"
    zengine_sort_field: str = "modified"
    zengine_max_pages: int = 20
    zengine_api_base_url: str = "https://api.zenginehq.com/v1"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    database_url: str = "sqlite:///data/monitor.db"
    check_interval_minutes: int = 10
    notify_existing_on_first_run: bool = False
    run_on_startup: bool = True
    run_once_secret: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            zengine_api_token=os.getenv("ZENGINE_API_TOKEN", "").strip(),
            zengine_login_email=os.getenv("ZENGINE_LOGIN_EMAIL", "").strip(),
            zengine_login_password=os.getenv("ZENGINE_LOGIN_PASSWORD", "").strip(),
            zengine_form_id=_int_env("ZENGINE_FORM_ID", 185672),
            zengine_status_field_id=os.getenv("ZENGINE_STATUS_FIELD_ID", "field3589680").strip(),
            zengine_approved_value=os.getenv("ZENGINE_APPROVED_VALUE", "Approved").strip(),
            zengine_amount_field_id=os.getenv("ZENGINE_AMOUNT_FIELD_ID", "field3583325").strip(),
            zengine_payment_type_field_id=os.getenv("ZENGINE_PAYMENT_TYPE_FIELD_ID", "field3609440").strip(),
            zengine_payment_memo_field_id=os.getenv("ZENGINE_PAYMENT_MEMO_FIELD_ID", "field6995603").strip(),
            zengine_linked_payee_field_id=os.getenv("ZENGINE_LINKED_PAYEE_FIELD_ID", "field3588097").strip(),
            zengine_sort_field=os.getenv("ZENGINE_SORT_FIELD", "modified").strip(),
            zengine_max_pages=_int_env("ZENGINE_MAX_PAGES", 20),
            zengine_api_base_url=os.getenv("ZENGINE_API_BASE_URL", "https://api.zenginehq.com/v1").strip(),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
            database_url=os.getenv("DATABASE_URL", "sqlite:///data/monitor.db").strip(),
            check_interval_minutes=_int_env("CHECK_INTERVAL_MINUTES", 10),
            notify_existing_on_first_run=_bool_env("NOTIFY_EXISTING_ON_FIRST_RUN", False),
            run_on_startup=_bool_env("RUN_ON_STARTUP", True),
            run_once_secret=os.getenv("RUN_ONCE_SECRET", "").strip(),
        )

    def missing_required_values(self) -> list[str]:
        missing = []
        if not self.zengine_api_token and not (
            self.zengine_login_email and self.zengine_login_password
        ):
            missing.extend(["ZENGINE_LOGIN_EMAIL", "ZENGINE_LOGIN_PASSWORD"])

        for env_name, value in {
            "ZENGINE_STATUS_FIELD_ID": self.zengine_status_field_id,
            "ZENGINE_PAYMENT_MEMO_FIELD_ID": self.zengine_payment_memo_field_id,
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
        }.items():
            if not value:
                missing.append(env_name)
        return missing
