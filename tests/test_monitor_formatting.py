import unittest

from monitor import DisbursementMonitor, _display_value, _format_amount
from settings import Settings


class MonitorFormattingTests(unittest.TestCase):
    def test_format_amount_numeric_string(self) -> None:
        self.assertEqual(_format_amount("1234.5"), "$1,234.50")

    def test_format_amount_preserves_non_numeric_value(self) -> None:
        self.assertEqual(_format_amount("TBD"), "$TBD")

    def test_display_value_uses_linked_record_name(self) -> None:
        self.assertEqual(_display_value({"id": 123, "name": "Jane Payee"}), "Jane Payee")

    def test_message_includes_payment_type(self) -> None:
        monitor = DisbursementMonitor.__new__(DisbursementMonitor)
        monitor.settings = Settings(zengine_api_token="token")
        message = monitor._build_message(
            {
                "field3583325": "1234.5",
                "field3609440": "ACH",
                "field6995603": "Housing support",
                "field3588097": {"name": "Jane Payee"},
            }
        )
        self.assertEqual(
            message,
            "New Disbursement Allocation added: $1,234.50 - ACH - Housing support - Jane Payee",
        )


if __name__ == "__main__":
    unittest.main()
