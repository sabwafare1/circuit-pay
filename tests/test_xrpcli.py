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


if __name__ == "__main__":
    unittest.main()
