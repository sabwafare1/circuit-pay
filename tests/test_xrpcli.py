import argparse
import contextlib
import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xrpcli

VALID_ADDRESS = "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"


def make_args(address=VALID_ADDRESS, network="mainnet", limit=20):
    return argparse.Namespace(address=address, network=network, limit=limit)


def make_request_args(address=VALID_ADDRESS, amount="10", note=None, tag=None):
    return argparse.Namespace(address=address, amount=amount, note=note, tag=tag)


class IsValidClassicAddressTests(unittest.TestCase):
    def test_accepts_valid_address(self):
        self.assertTrue(xrpcli.is_valid_classic_address(VALID_ADDRESS))

    def test_rejects_bad_checksum(self):
        # Same length/alphabet as a real address, but not a real one.
        self.assertFalse(
            xrpcli.is_valid_classic_address("rNQEMJA6UgobNJ7uJHtokzJcPUcm9rzMNW")
        )

    def test_rejects_invalid_characters(self):
        self.assertFalse(xrpcli.is_valid_classic_address("not-an-address"))

    def test_rejects_wrong_length(self):
        self.assertFalse(xrpcli.is_valid_classic_address("r123"))

    def test_rejects_empty_string(self):
        self.assertFalse(xrpcli.is_valid_classic_address(""))


class CmdHistoryTests(unittest.TestCase):
    @patch("xrpcli.rpc_call")
    def test_rejects_invalid_address_without_network_call(self, mock_rpc_call):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_history(make_args(address="not-an-address"))

        self.assertIn("not a valid XRPL wallet address", str(ctx.exception))
        mock_rpc_call.assert_not_called()

    @patch("xrpcli.rpc_call")
    def test_prints_transactions_on_success(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "transactions": [
                    {
                        "tx": {
                            "date": 820000000,
                            "TransactionType": "Payment",
                            "hash": "ABC123",
                        },
                        "meta": {"TransactionResult": "tesSUCCESS"},
                    }
                ],
            }
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_history(make_args())

        output = buf.getvalue()
        self.assertIn("Payment", output)
        self.assertIn("hash=ABC123", output)
        self.assertIn("result=tesSUCCESS", output)

    @patch("xrpcli.rpc_call")
    def test_prints_message_when_no_transactions(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "success", "transactions": []}
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_history(make_args())

        self.assertIn("No transactions found", buf.getvalue())

    @patch("xrpcli.rpc_call")
    def test_surfaces_friendly_error_for_account_not_found(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error": "actNotFound"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_history(make_args())

        self.assertIn("account not found", str(ctx.exception))


class XrpToDropsTests(unittest.TestCase):
    def test_converts_whole_and_fractional_amounts(self):
        self.assertEqual(xrpcli.xrp_to_drops("12.5"), 12500000)
        self.assertEqual(xrpcli.xrp_to_drops("3"), 3000000)
        self.assertEqual(xrpcli.xrp_to_drops("0.000001"), 1)

    def test_rejects_zero_or_negative(self):
        with self.assertRaises(SystemExit):
            xrpcli.xrp_to_drops("0")
        with self.assertRaises(SystemExit):
            xrpcli.xrp_to_drops("-5")

    def test_rejects_more_than_six_decimal_places(self):
        with self.assertRaises(SystemExit):
            xrpcli.xrp_to_drops("1.1234567")

    def test_rejects_non_numeric_amount(self):
        with self.assertRaises(SystemExit):
            xrpcli.xrp_to_drops("abc")


class BuildPaymentUriTests(unittest.TestCase):
    def test_includes_address_amount_and_tag(self):
        uri = xrpcli.build_payment_uri(VALID_ADDRESS, "12.5", 777, None)
        self.assertEqual(
            uri, f"ripple:{VALID_ADDRESS}?amount=12.5&dt=777"
        )

    def test_includes_url_encoded_note_when_given(self):
        uri = xrpcli.build_payment_uri(VALID_ADDRESS, "3", 5, "Invoice #42")
        self.assertIn("memo=Invoice+%2342", uri)


class CmdRequestTests(unittest.TestCase):
    def test_rejects_invalid_address(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(address="not-an-address"))

        self.assertIn("not a valid XRPL wallet address", str(ctx.exception))

    def test_rejects_invalid_amount(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(amount="0"))

        self.assertIn("amount must be greater than zero", str(ctx.exception))

    def test_rejects_tag_out_of_range(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(tag=2**32))

        self.assertIn("--tag must be between", str(ctx.exception))

    def test_uses_provided_tag_and_prints_request_details(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(
                make_request_args(amount="12.5", note="Invoice #42", tag=777)
            )

        output = buf.getvalue()
        self.assertIn(VALID_ADDRESS, output)
        self.assertIn("12.5 XRP (12500000 drops)", output)
        self.assertIn("Destination tag:  777", output)
        self.assertIn("Note:             Invoice #42", output)
        self.assertIn(f"ripple:{VALID_ADDRESS}?amount=12.5&dt=777&memo=Invoice", output)

        self.assertIn('"DestinationTag": 777', output)
        self.assertIn('"Amount": "12500000"', output)
        self.assertIn('"MemoData"', output)

    def test_omits_memo_and_note_line_when_no_note_given(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(amount="3", tag=5))

        output = buf.getvalue()
        self.assertNotIn("Note:", output)
        self.assertNotIn("Memos", output)
        self.assertNotIn("memo=", output)

    @patch("xrpcli.secrets.randbelow")
    def test_generates_random_tag_when_not_provided(self, mock_randbelow):
        mock_randbelow.return_value = 41

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(tag=None))

        self.assertIn("Destination tag:  42", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
