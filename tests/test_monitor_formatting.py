import unittest

from monitor import _display_value, _format_amount


class MonitorFormattingTests(unittest.TestCase):
    def test_format_amount_numeric_string(self) -> None:
        self.assertEqual(_format_amount("1234.5"), "$1,234.50")

    def test_format_amount_preserves_non_numeric_value(self) -> None:
        self.assertEqual(_format_amount("TBD"), "$TBD")

    def test_display_value_uses_linked_record_name(self) -> None:
        self.assertEqual(_display_value({"id": 123, "name": "Jane Payee"}), "Jane Payee")


if __name__ == "__main__":
    unittest.main()
