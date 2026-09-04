import argparse
import builtins
import contextlib
import hashlib
import hmac
import io
import json
import os
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xrpcli

VALID_ADDRESS = "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"

USD_RATE_RESPONSE = {"ripple": {"usd": 1.0}}
NETWORK_FEE_RESPONSE = {"result": {"status": "success", "drops": {"base_fee": "10"}}}
PAY_ENV = {
    "XRPL_SECRET": "sEdTest",
    "PLATFORM_FEE_ADDRESS": "rFeeCollector",
    "VERIFF_API_KEY": "test-api-key",
    "VERIFF_SHARED_SECRET": "test-shared-secret",
}
APPROVED_VERIFICATION_STORE = {
    "rPayerAddress": {
        "session_id": "sess-1",
        "session_url": "https://veriff.example/sessions/sess-1",
        "status": "approved",
        "created_at": "2026-08-16T00:00:00+00:00",
        "checked_at": "2026-08-16T00:00:00+00:00",
    }
}


def make_args(address=VALID_ADDRESS, network="mainnet", limit=20):
    return argparse.Namespace(address=address, network=network, limit=limit)


def make_request_args(
    address=VALID_ADDRESS,
    amount="10",
    note=None,
    tag=None,
    network="mainnet",
    fee_type="p2p",
):
    return argparse.Namespace(
        address=address,
        amount=amount,
        note=note,
        tag=tag,
        network=network,
        fee_type=fee_type,
    )


def make_pay_args(request_id="abc123"):
    return argparse.Namespace(request_id=request_id)


def make_send_stablecoin_args(
    destination=VALID_ADDRESS,
    amount="25",
    symbol="USDC",
    tag=None,
    network="mainnet",
    fee_type="p2p",
):
    return argparse.Namespace(
        destination=destination,
        amount=amount,
        symbol=symbol,
        tag=tag,
        network=network,
        fee_type=fee_type,
    )


def make_check_args(request_id="abc123", limit=50):
    return argparse.Namespace(request_id=request_id, limit=limit)


def make_account_tx_entry(
    tx_type="Payment",
    result="tesSUCCESS",
    destination=VALID_ADDRESS,
    destination_tag=42,
    amount="5000000",
    account="rPayerAddress",
    tx_hash="MATCHHASH",
):
    return {
        "tx": {
            "TransactionType": tx_type,
            "Destination": destination,
            "DestinationTag": destination_tag,
            "Amount": amount,
            "Account": account,
            "hash": tx_hash,
        },
        "meta": {"TransactionResult": result},
    }


def make_balance_args(address=VALID_ADDRESS, network="mainnet"):
    return argparse.Namespace(address=address, network=network)


def make_price_args(currency="usd"):
    return argparse.Namespace(currency=currency)


def make_convert_args(amount="100", unit="xrp"):
    return argparse.Namespace(amount=amount, unit=unit)


class FakeJsonResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


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

    @patch("xrpcli.rpc_call")
    def test_surfaces_error_message_for_unmapped_rpc_error(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {
                "status": "error",
                "error": "someUnmappedCode",
                "error_message": "Something specific went wrong.",
            }
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_history(make_args())

        self.assertIn("Something specific went wrong.", str(ctx.exception))

    @patch("xrpcli.rpc_call")
    def test_surfaces_raw_error_code_when_no_message_available(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error": "someUnmappedCode"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_history(make_args())

        self.assertIn("someUnmappedCode", str(ctx.exception))


class CmdBalanceTests(unittest.TestCase):
    @patch("xrpcli.rpc_call")
    def test_rejects_invalid_address_without_network_call(self, mock_rpc_call):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_balance(make_balance_args(address="not-an-address"))

        self.assertIn("not a valid XRPL wallet address", str(ctx.exception))
        mock_rpc_call.assert_not_called()

    @patch("xrpcli.rpc_call")
    def test_prints_balance_on_success(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "account_data": {"Balance": "56774125592"},
            }
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_balance(make_balance_args())

        output = buf.getvalue()
        self.assertIn(VALID_ADDRESS, output)
        self.assertIn("56774.125592 XRP", output)
        self.assertIn("56774125592 drops", output)
        self.assertIn("mainnet", output)

    @patch("xrpcli.rpc_call")
    def test_surfaces_friendly_error_for_account_not_found(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error": "actNotFound"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_balance(make_balance_args())

        self.assertIn("account not found", str(ctx.exception))

    @patch("xrpcli.rpc_call")
    def test_surfaces_error_message_for_unmapped_rpc_error(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {
                "status": "error",
                "error": "someUnmappedCode",
                "error_message": "Something specific went wrong.",
            }
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_balance(make_balance_args())

        self.assertIn("Something specific went wrong.", str(ctx.exception))

    @patch("xrpcli.rpc_call")
    def test_surfaces_raw_error_code_when_no_message_available(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error": "someUnmappedCode"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_balance(make_balance_args())

        self.assertIn("someUnmappedCode", str(ctx.exception))


class CmdStablecoinsTests(unittest.TestCase):
    @patch("xrpcli.rpc_call")
    def test_rejects_invalid_address_without_network_call(self, mock_rpc_call):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_stablecoins(make_balance_args(address="not-an-address"))

        self.assertIn("not a valid XRPL wallet address", str(ctx.exception))
        mock_rpc_call.assert_not_called()

    @patch("xrpcli.rpc_call")
    def test_prints_known_balance_and_no_trust_line_for_the_rest(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "lines": [
                    {
                        "account": xrpcli.STABLECOINS["RLUSD"]["issuers"]["mainnet"],
                        "currency": xrpcli.STABLECOINS["RLUSD"]["currency"],
                        "balance": "12.5",
                    },
                    {
                        "account": "rSomeUnrelatedIssuer",
                        "currency": "4E4F4E4445580000000000000000000000000000",
                        "balance": "999",
                    },
                ],
            }
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_stablecoins(make_balance_args())

        output = buf.getvalue()
        self.assertIn(VALID_ADDRESS, output)
        self.assertIn("mainnet", output)
        self.assertIn("RLUSD: 12.5", output)
        self.assertIn("USDC: no trust line", output)

    @patch("xrpcli.rpc_call")
    def test_rejects_network_with_no_known_issuers(self, mock_rpc_call):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_stablecoins(make_balance_args(network="devnet"))

        self.assertIn("no known stablecoin issuers", str(ctx.exception))
        mock_rpc_call.assert_not_called()

    @patch("xrpcli.rpc_call")
    def test_surfaces_friendly_error_for_account_not_found(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error": "actNotFound"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_stablecoins(make_balance_args())

        self.assertIn("account not found", str(ctx.exception))


class RpcCallTests(unittest.TestCase):
    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_clean_error_when_network_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.rpc_call(xrpcli.NETWORKS["mainnet"], "account_info", {})

        self.assertIn("failed to reach", str(ctx.exception))
        self.assertIn(xrpcli.NETWORKS["mainnet"], str(ctx.exception))


class FetchPriceTests(unittest.TestCase):
    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_clean_error_when_price_api_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.fetch_price("usd")

        self.assertIn("failed to reach price API", str(ctx.exception))


class CmdPriceTests(unittest.TestCase):
    @patch("xrpcli.fetch_price")
    def test_prints_price_on_success(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"usd": 1.001}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_price(make_price_args())

        self.assertIn("1 XRP = 1.001 USD", buf.getvalue())

    @patch("xrpcli.fetch_price")
    def test_lowercases_currency_before_lookup(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"eur": 0.864225}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_price(make_price_args(currency="EUR"))

        mock_fetch_price.assert_called_once_with("eur")
        self.assertIn("1 XRP = 0.864225 EUR", buf.getvalue())

    @patch("xrpcli.fetch_price")
    def test_raises_when_currency_missing_from_response(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {}}

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_price(make_price_args(currency="notarealcurrency"))

        self.assertIn("no price data for currency", str(ctx.exception))

    @patch("xrpcli.fetch_price")
    def test_uppercases_mixed_case_currency_input(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"usd": 1.001}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_price(make_price_args(currency="UsD"))

        mock_fetch_price.assert_called_once_with("usd")
        self.assertIn("1 XRP = 1.001 USD", buf.getvalue())

    def test_uppercases_various_currency_codes(self):
        for currency, price in [("jpy", 150), ("gbp", 0.79), ("btc", 0.0000123)]:
            with self.subTest(currency=currency), patch("xrpcli.fetch_price") as mock_fetch_price:
                mock_fetch_price.return_value = {"ripple": {currency: price}}

                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    xrpcli.cmd_price(make_price_args(currency=currency))

                self.assertIn(
                    f"1 XRP = {price} {currency.upper()}", buf.getvalue()
                )

    @patch("xrpcli.fetch_price")
    def test_formats_integer_price_without_decimal_artifacts(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"jpy": 150}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_price(make_price_args(currency="jpy"))

        self.assertIn("1 XRP = 150 JPY", buf.getvalue())
        self.assertNotIn("150.0", buf.getvalue())


class CmdConvertTests(unittest.TestCase):
    @patch("xrpcli.fetch_price")
    def test_converts_xrp_to_usd(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"usd": 1.001}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_convert(make_convert_args(amount="100", unit="xrp"))

        output = buf.getvalue()
        self.assertIn("100 XRP = 100.10 USD", output)
        self.assertIn("rate: 1 XRP = 1.001 USD", output)

    @patch("xrpcli.fetch_price")
    def test_converts_usd_to_xrp(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"usd": 1.001}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_convert(make_convert_args(amount="50", unit="usd"))

        self.assertIn("50 USD = 49.950050 XRP", buf.getvalue())

    @patch("xrpcli.fetch_price")
    def test_unit_is_case_insensitive(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"usd": 1.001}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_convert(make_convert_args(amount="10", unit="XRP"))

        self.assertIn("10 XRP = 10.01 USD", buf.getvalue())

    @patch("xrpcli.fetch_price")
    def test_rejects_invalid_unit_without_fetching_price(self, mock_fetch_price):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_convert(make_convert_args(unit="eur"))

        self.assertIn("unit must be 'xrp' or 'usd'", str(ctx.exception))
        mock_fetch_price.assert_not_called()

    @patch("xrpcli.fetch_price")
    def test_rejects_non_numeric_amount(self, mock_fetch_price):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_convert(make_convert_args(amount="abc"))

        self.assertIn("not a valid amount", str(ctx.exception))
        mock_fetch_price.assert_not_called()

    @patch("xrpcli.fetch_price")
    def test_rejects_zero_or_negative_amount(self, mock_fetch_price):
        with self.assertRaises(SystemExit):
            xrpcli.cmd_convert(make_convert_args(amount="0"))
        with self.assertRaises(SystemExit):
            xrpcli.cmd_convert(make_convert_args(amount="-5"))
        mock_fetch_price.assert_not_called()

    @patch("xrpcli.fetch_price")
    def test_raises_when_no_usd_price_available(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {}}

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_convert(make_convert_args())

        self.assertIn("no price data available", str(ctx.exception))


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


class CalculatePlatformFeeUsdTests(unittest.TestCase):
    def test_p2p_is_a_flat_dime_regardless_of_amount(self):
        self.assertEqual(
            xrpcli.calculate_platform_fee_usd(xrpcli.decimal.Decimal("2"), "p2p"),
            xrpcli.decimal.Decimal("0.10"),
        )
        self.assertEqual(
            xrpcli.calculate_platform_fee_usd(xrpcli.decimal.Decimal("50000"), "p2p"),
            xrpcli.decimal.Decimal("0.10"),
        )

    def test_merchant_charges_half_a_percent_between_the_clamps(self):
        # 0.5% of $2000 is $10, right at the minimum.
        self.assertEqual(
            xrpcli.calculate_platform_fee_usd(xrpcli.decimal.Decimal("2000"), "merchant"),
            xrpcli.decimal.Decimal("10.00"),
        )
        # 0.5% of $4000 is $20, comfortably between the clamps.
        self.assertEqual(
            xrpcli.calculate_platform_fee_usd(xrpcli.decimal.Decimal("4000"), "merchant"),
            xrpcli.decimal.Decimal("20.00"),
        )

    def test_merchant_fee_is_floored_at_ten_dollars(self):
        self.assertEqual(
            xrpcli.calculate_platform_fee_usd(xrpcli.decimal.Decimal("10"), "merchant"),
            xrpcli.decimal.Decimal("10.00"),
        )

    def test_merchant_fee_is_capped_at_five_thousand_dollars(self):
        self.assertEqual(
            xrpcli.calculate_platform_fee_usd(xrpcli.decimal.Decimal("5000000"), "merchant"),
            xrpcli.decimal.Decimal("5000.00"),
        )


class UsdToDropsTests(unittest.TestCase):
    def test_converts_using_the_given_rate(self):
        # $10 at a rate of 1 XRP = $2 is 5 XRP = 5,000,000 drops.
        self.assertEqual(
            xrpcli.usd_to_drops(xrpcli.decimal.Decimal("10"), xrpcli.decimal.Decimal("2")),
            5000000,
        )


class GetUsdRateTests(unittest.TestCase):
    @patch("xrpcli.fetch_price")
    def test_returns_decimal_rate_from_price_response(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {"usd": 1.001}}
        self.assertEqual(xrpcli.get_usd_rate(), xrpcli.decimal.Decimal("1.001"))

    @patch("xrpcli.fetch_price")
    def test_raises_when_no_usd_price_available(self, mock_fetch_price):
        mock_fetch_price.return_value = {"ripple": {}}
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.get_usd_rate()
        self.assertIn("no price data available", str(ctx.exception))


class FetchNetworkFeeDropsTests(unittest.TestCase):
    @patch("xrpcli.rpc_call")
    def test_returns_base_fee_in_drops(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "success", "drops": {"base_fee": "10"}}
        }
        self.assertEqual(
            xrpcli.fetch_network_fee_drops(xrpcli.NETWORKS["mainnet"]), 10
        )

    @patch("xrpcli.rpc_call")
    def test_surfaces_rpc_error(self, mock_rpc_call):
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error_message": "Fee lookup failed."}
        }
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.fetch_network_fee_drops(xrpcli.NETWORKS["mainnet"])
        self.assertIn("Fee lookup failed.", str(ctx.exception))


class VeriffSignatureTests(unittest.TestCase):
    def test_matches_hmac_sha256_hex_digest(self):
        payload = b'{"verification":{"vendorData":"rSomeAddress"}}'
        expected = hmac.new(b"my-secret", payload, hashlib.sha256).hexdigest()
        self.assertEqual(xrpcli.veriff_signature("my-secret", payload), expected)

    def test_different_payloads_produce_different_signatures(self):
        sig_a = xrpcli.veriff_signature("my-secret", b"payload-a")
        sig_b = xrpcli.veriff_signature("my-secret", b"payload-b")
        self.assertNotEqual(sig_a, sig_b)


class CreateVeriffSessionTests(unittest.TestCase):
    @patch("xrpcli.urllib.request.urlopen")
    def test_returns_session_id_and_url_and_signs_the_request(self, mock_urlopen):
        mock_urlopen.return_value = FakeJsonResponse(
            {
                "verification": {
                    "id": "sess-1",
                    "url": "https://veriff.example/sessions/sess-1",
                }
            }
        )

        session_id, session_url = xrpcli.create_veriff_session(
            VALID_ADDRESS, "test-api-key", "test-shared-secret"
        )

        self.assertEqual(session_id, "sess-1")
        self.assertEqual(session_url, "https://veriff.example/sessions/sess-1")

        sent_req = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_req.full_url, f"{xrpcli.VERIFF_BASE_URL}/sessions")
        self.assertEqual(sent_req.get_header("X-auth-client"), "test-api-key")
        expected_signature = hmac.new(
            b"test-shared-secret", sent_req.data, hashlib.sha256
        ).hexdigest()
        self.assertEqual(sent_req.get_header("X-hmac-signature"), expected_signature)
        self.assertEqual(
            json.loads(sent_req.data), {"verification": {"vendorData": VALID_ADDRESS}}
        )

    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_clean_error_when_veriff_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.create_veriff_session(VALID_ADDRESS, "key", "secret")

        self.assertIn("failed to reach Veriff API", str(ctx.exception))

    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_on_unexpected_response_shape(self, mock_urlopen):
        mock_urlopen.return_value = FakeJsonResponse({"verification": {}})

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.create_veriff_session(VALID_ADDRESS, "key", "secret")

        self.assertIn("unexpected response from Veriff", str(ctx.exception))


class FetchVeriffDecisionTests(unittest.TestCase):
    @patch("xrpcli.urllib.request.urlopen")
    def test_returns_status_and_signs_the_request(self, mock_urlopen):
        mock_urlopen.return_value = FakeJsonResponse(
            {"verification": {"status": "approved"}}
        )

        status = xrpcli.fetch_veriff_decision("sess-1", "test-api-key", "test-shared-secret")

        self.assertEqual(status, "approved")

        sent_req = mock_urlopen.call_args[0][0]
        self.assertEqual(
            sent_req.full_url, f"{xrpcli.VERIFF_BASE_URL}/sessions/sess-1/decision"
        )
        self.assertEqual(sent_req.get_header("X-auth-client"), "test-api-key")
        expected_signature = hmac.new(
            b"test-shared-secret", b"sess-1", hashlib.sha256
        ).hexdigest()
        self.assertEqual(sent_req.get_header("X-hmac-signature"), expected_signature)

    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_clean_error_when_veriff_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.fetch_veriff_decision("sess-1", "key", "secret")

        self.assertIn("failed to reach Veriff API", str(ctx.exception))

    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_on_unexpected_response_shape(self, mock_urlopen):
        mock_urlopen.return_value = FakeJsonResponse({"verification": {}})

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.fetch_veriff_decision("sess-1", "key", "secret")

        self.assertIn("unexpected response from Veriff", str(ctx.exception))

    @patch("xrpcli.urllib.request.urlopen")
    def test_null_verification_means_pending_not_an_error(self, mock_urlopen):
        # Confirmed against the real Veriff API: before the session is
        # completed, GET .../decision returns {"status": "success",
        # "verification": null} -- this is the normal "no decision yet"
        # state, not a malformed response.
        mock_urlopen.return_value = FakeJsonResponse(
            {"status": "success", "verification": None}
        )

        status = xrpcli.fetch_veriff_decision("sess-1", "key", "secret")

        self.assertEqual(status, "pending")

    @patch("xrpcli.urllib.request.urlopen")
    def test_raises_when_verification_key_missing_entirely(self, mock_urlopen):
        mock_urlopen.return_value = FakeJsonResponse({"status": "success"})

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.fetch_veriff_decision("sess-1", "key", "secret")

        self.assertIn("unexpected response from Veriff", str(ctx.exception))


class EnsurePayerVerifiedTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"VERIFF_API_KEY": "test-api-key", "VERIFF_SHARED_SECRET": "test-shared-secret"},
        clear=True,
    )
    @patch("xrpcli.create_veriff_session")
    @patch("xrpcli.fetch_veriff_decision")
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    def test_returns_silently_when_already_approved(
        self, mock_load_verifications, mock_fetch_decision, mock_create_session
    ):
        xrpcli.ensure_payer_verified("rPayerAddress")
        mock_fetch_decision.assert_not_called()
        mock_create_session.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_veriff_credentials(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.ensure_payer_verified("rPayerAddress")

        self.assertIn("VERIFF_API_KEY", str(ctx.exception))
        self.assertIn("VERIFF_SHARED_SECRET", str(ctx.exception))

    @patch.dict(
        os.environ,
        {"VERIFF_API_KEY": "test-api-key", "VERIFF_SHARED_SECRET": "test-shared-secret"},
        clear=True,
    )
    @patch("xrpcli.save_verifications")
    @patch("xrpcli.load_verifications", return_value={})
    @patch("xrpcli.create_veriff_session")
    def test_creates_a_session_on_first_call_and_blocks(
        self, mock_create_session, mock_load_verifications, mock_save_verifications
    ):
        mock_create_session.return_value = ("sess-new", "https://veriff.example/sess-new")

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.ensure_payer_verified("rPayerAddress")

        self.assertIn("https://veriff.example/sess-new", str(ctx.exception))
        saved = mock_save_verifications.call_args[0][0]
        self.assertEqual(saved["rPayerAddress"]["status"], "created")
        self.assertEqual(saved["rPayerAddress"]["session_id"], "sess-new")

    @patch.dict(
        os.environ,
        {"VERIFF_API_KEY": "test-api-key", "VERIFF_SHARED_SECRET": "test-shared-secret"},
        clear=True,
    )
    @patch("xrpcli.save_verifications")
    @patch("xrpcli.load_verifications")
    @patch("xrpcli.fetch_veriff_decision")
    def test_polls_and_proceeds_when_pending_becomes_approved(
        self, mock_fetch_decision, mock_load_verifications, mock_save_verifications
    ):
        mock_load_verifications.return_value = {
            "rPayerAddress": {
                "session_id": "sess-1",
                "session_url": "https://veriff.example/sess-1",
                "status": "created",
            }
        }
        mock_fetch_decision.return_value = "approved"

        xrpcli.ensure_payer_verified("rPayerAddress")  # should not raise

        saved = mock_save_verifications.call_args[0][0]
        self.assertEqual(saved["rPayerAddress"]["status"], "approved")

    @patch.dict(
        os.environ,
        {"VERIFF_API_KEY": "test-api-key", "VERIFF_SHARED_SECRET": "test-shared-secret"},
        clear=True,
    )
    @patch("xrpcli.save_verifications")
    @patch("xrpcli.load_verifications")
    @patch("xrpcli.fetch_veriff_decision")
    def test_polls_and_blocks_when_still_not_approved(
        self, mock_fetch_decision, mock_load_verifications, mock_save_verifications
    ):
        mock_load_verifications.return_value = {
            "rPayerAddress": {
                "session_id": "sess-1",
                "session_url": "https://veriff.example/sess-1",
                "status": "created",
            }
        }
        mock_fetch_decision.return_value = "declined"

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.ensure_payer_verified("rPayerAddress")

        self.assertIn("not approved yet", str(ctx.exception))
        self.assertIn("'declined'", str(ctx.exception))
        saved = mock_save_verifications.call_args[0][0]
        self.assertEqual(saved["rPayerAddress"]["status"], "declined")


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

    def test_rejects_negative_amount(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(amount="-5"))

        self.assertIn("amount must be greater than zero", str(ctx.exception))

    def test_rejects_non_numeric_amount(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(amount="abc"))

        self.assertIn("not a valid XRP amount", str(ctx.exception))

    def test_rejects_amount_with_too_many_decimal_places(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(amount="1.1234567"))

        self.assertIn("at most 6 decimal places", str(ctx.exception))

    def test_rejects_tag_out_of_range(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(tag=2**32))

        self.assertIn("--tag must be between", str(ctx.exception))

    def test_rejects_negative_tag(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_request(make_request_args(tag=-1))

        self.assertIn("--tag must be between", str(ctx.exception))

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_rejected_request_never_touches_the_store(
        self, mock_load_requests, mock_save_requests
    ):
        with self.assertRaises(SystemExit):
            xrpcli.cmd_request(make_request_args(address="not-an-address"))
        with self.assertRaises(SystemExit):
            xrpcli.cmd_request(make_request_args(amount="0"))
        with self.assertRaises(SystemExit):
            xrpcli.cmd_request(make_request_args(tag=2**32))

        mock_load_requests.assert_not_called()
        mock_save_requests.assert_not_called()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_uses_provided_tag_and_prints_request_details(
        self, mock_load_requests, mock_save_requests
    ):
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

        mock_save_requests.assert_called_once()
        saved = mock_save_requests.call_args[0][0]
        self.assertEqual(len(saved), 1)
        entry = next(iter(saved.values()))
        self.assertEqual(entry["address"], VALID_ADDRESS)
        self.assertEqual(entry["amount"], "12.5")
        self.assertEqual(entry["tag"], 777)
        self.assertEqual(entry["note"], "Invoice #42")
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["fee_type"], "p2p")

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_defaults_to_p2p_fee_type_and_prints_flat_fee(
        self, mock_load_requests, mock_save_requests
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args())

        self.assertIn("Fee type:         p2p (flat $0.10 fee)", buf.getvalue())

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_merchant_type_is_stored_and_printed(
        self, mock_load_requests, mock_save_requests
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(fee_type="merchant"))

        output = buf.getvalue()
        self.assertIn(
            "Fee type:         merchant (0.5% fee (min $10.00, max $5000.00))",
            output,
        )

        saved = mock_save_requests.call_args[0][0]
        entry = next(iter(saved.values()))
        self.assertEqual(entry["fee_type"], "merchant")

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_omits_memo_and_note_line_when_no_note_given(
        self, mock_load_requests, mock_save_requests
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(amount="3", tag=5))

        output = buf.getvalue()
        self.assertNotIn("Note:", output)
        self.assertNotIn("Memos", output)
        self.assertNotIn("memo=", output)

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    @patch("xrpcli.secrets.randbelow")
    def test_generates_random_tag_when_not_provided(
        self, mock_randbelow, mock_load_requests, mock_save_requests
    ):
        mock_randbelow.return_value = 41

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(tag=None))

        self.assertIn("Destination tag:  42", buf.getvalue())

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests")
    def test_avoids_id_collision_with_existing_requests(
        self, mock_load_requests, mock_save_requests
    ):
        mock_load_requests.return_value = {"aaaaaaaa": {"status": "pending"}}

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args())

        saved = mock_save_requests.call_args[0][0]
        self.assertEqual(len(saved), 2)
        self.assertIn("aaaaaaaa", saved)

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_prints_scannable_ascii_qr_code_for_the_payment_uri(
        self, mock_load_requests, mock_save_requests
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(amount="12.5", tag=777))

        output = buf.getvalue()
        self.assertIn("Or have them scan this to pay:", output)
        self.assertIn("##", output)

    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests", return_value={})
    def test_prints_install_hint_instead_of_crashing_when_qrcode_not_installed(
        self, mock_load_requests, mock_save_requests
    ):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "qrcode":
                raise ImportError("No module named 'qrcode'")
            return real_import(name, *args, **kwargs)

        buf = io.StringIO()
        with patch("builtins.__import__", side_effect=fake_import), contextlib.redirect_stdout(buf):
            xrpcli.cmd_request(make_request_args(amount="12.5", tag=777))

        output = buf.getvalue()
        self.assertIn("pip install qrcode", output)
        self.assertNotIn("Or have them scan this to pay:", output)
        # The request itself still succeeds even without the optional dependency.
        mock_save_requests.assert_called_once()


class RenderQrAsciiTests(unittest.TestCase):
    def test_renders_a_grid_of_two_char_wide_modules(self):
        art = xrpcli.render_qr_ascii("ripple:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh?amount=5&dt=1")

        lines = art.split("\n")
        self.assertGreater(len(lines), 0)
        for line in lines:
            self.assertEqual(len(line) % 2, 0)
            chunks = [line[i : i + 2] for i in range(0, len(line), 2)]
            self.assertTrue(all(chunk in ("##", "  ") for chunk in chunks))
        # A real QR code has both dark and light modules.
        self.assertIn("##", art)
        self.assertIn("  ", art)

    def test_different_data_produces_different_codes(self):
        art_a = xrpcli.render_qr_ascii("ripple:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh?amount=5&dt=1")
        art_b = xrpcli.render_qr_ascii("ripple:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh?amount=50&dt=2")

        self.assertNotEqual(art_a, art_b)


class CmdPayTests(unittest.TestCase):
    @patch("xrpcli.load_requests", return_value={})
    def test_rejects_unknown_request_id(self, mock_load_requests):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args(request_id="doesnotexist"))

        self.assertIn("no payment request found", str(ctx.exception))

    @patch("xrpcli.load_requests")
    def test_rejects_already_paid_request(self, mock_load_requests):
        mock_load_requests.return_value = {
            "abc123": {"status": "paid", "tx_hash": "DEADBEEF"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("already paid", str(ctx.exception))
        self.assertIn("DEADBEEF", str(ctx.exception))

    @patch.dict(os.environ, {}, clear=True)
    @patch("xrpcli.load_requests")
    def test_requires_secret_env_var(self, mock_load_requests):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("XRPL_SECRET", str(ctx.exception))

    @patch.dict(os.environ, {"XRPL_SECRET": "sEdTest"}, clear=True)
    @patch("xrpcli.load_requests")
    def test_requires_platform_fee_address_env_var(self, mock_load_requests):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("PLATFORM_FEE_ADDRESS", str(ctx.exception))

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_requests")
    def test_reports_missing_dependency_when_xrpl_py_not_installed(
        self, mock_load_requests
    ):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "xrpl" or name.startswith("xrpl."):
                raise ImportError("No module named 'xrpl'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("xrpl-py", str(ctx.exception))
        self.assertIn("pip install -r requirements.txt", str(ctx.exception))

    @patch.dict(
        os.environ,
        {**PAY_ENV, "XRPL_SECRET": "not-a-real-seed"},
        clear=True,
    )
    @patch("xrpcli.load_requests")
    def test_reports_invalid_secret(self, mock_load_requests):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }

        with patch(
            "xrpl.wallet.Wallet.from_seed", side_effect=ValueError("bad checksum")
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("invalid XRPL_SECRET", str(ctx.exception))
        self.assertIn("bad checksum", str(ctx.exception))

    @patch.dict(
        os.environ,
        {"XRPL_SECRET": "sEdTest", "PLATFORM_FEE_ADDRESS": "rFeeCollector"},
        clear=True,
    )
    @patch("xrpcli.load_requests")
    def test_requires_veriff_credentials_env_vars(self, mock_load_requests):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch(
            "xrpl.wallet.Wallet.from_seed", return_value=mock_wallet
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("VERIFF_API_KEY", str(ctx.exception))
        self.assertIn("VERIFF_SHARED_SECRET", str(ctx.exception))

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.create_veriff_session")
    @patch("xrpcli.save_verifications")
    @patch("xrpcli.load_verifications", return_value={})
    @patch("xrpcli.load_requests")
    def test_first_payment_creates_veriff_session_and_blocks(
        self,
        mock_load_requests,
        mock_load_verifications,
        mock_save_verifications,
        mock_create_session,
    ):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }
        mock_create_session.return_value = (
            "sess-new",
            "https://veriff.example/sessions/sess-new",
        )

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch(
            "xrpl.wallet.Wallet.from_seed", return_value=mock_wallet
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        mock_create_session.assert_called_once_with(
            "rPayerAddress", "test-api-key", "test-shared-secret"
        )
        self.assertIn("has not completed identity verification", str(ctx.exception))
        self.assertIn("https://veriff.example/sessions/sess-new", str(ctx.exception))

        saved = mock_save_verifications.call_args[0][0]
        self.assertEqual(saved["rPayerAddress"]["status"], "created")
        self.assertEqual(saved["rPayerAddress"]["session_id"], "sess-new")

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.fetch_veriff_decision")
    @patch("xrpcli.save_verifications")
    @patch("xrpcli.load_verifications")
    @patch("xrpcli.load_requests")
    def test_blocks_while_pending_verification_is_not_yet_approved(
        self,
        mock_load_requests,
        mock_load_verifications,
        mock_save_verifications,
        mock_fetch_decision,
    ):
        mock_load_requests.return_value = {
            "abc123": {
                "status": "pending",
                "address": VALID_ADDRESS,
                "amount": "5",
                "tag": 1,
                "note": None,
                "network": "mainnet",
            }
        }
        mock_load_verifications.return_value = {
            "rPayerAddress": {
                "session_id": "sess-1",
                "session_url": "https://veriff.example/sessions/sess-1",
                "status": "created",
            }
        }
        mock_fetch_decision.return_value = "submitted"

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch(
            "xrpl.wallet.Wallet.from_seed", return_value=mock_wallet
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        mock_fetch_decision.assert_called_once_with(
            "sess-1", "test-api-key", "test-shared-secret"
        )
        self.assertIn("not approved yet", str(ctx.exception))
        self.assertIn("'submitted'", str(ctx.exception))

        saved = mock_save_verifications.call_args[0][0]
        self.assertEqual(saved["rPayerAddress"]["status"], "submitted")

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests")
    def test_reports_submission_failure(
        self,
        mock_load_requests,
        mock_save_requests,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        entry = {
            "status": "pending",
            "address": VALID_ADDRESS,
            "amount": "5",
            "tag": 42,
            "note": None,
            "network": "mainnet",
        }
        mock_load_requests.return_value = {"abc123": entry}

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=Exception("connection refused"),
        ), patch("xrpl.clients.JsonRpcClient"), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("payment submission failed", str(ctx.exception))
        self.assertIn("connection refused", str(ctx.exception))
        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests")
    def test_submits_payment_and_marks_request_paid_on_success(
        self,
        mock_load_requests,
        mock_save_requests,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        entry = {
            "status": "pending",
            "address": VALID_ADDRESS,
            "amount": "5",
            "tag": 42,
            "note": "Invoice #42",
            "network": "mainnet",
        }
        mock_load_requests.return_value = {"abc123": entry}

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        main_response = unittest.mock.Mock()
        main_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "TXHASH123",
        }
        fee_response = unittest.mock.Mock()
        fee_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "FEETXHASH",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=[main_response, fee_response],
        ) as mock_submit, patch("xrpl.clients.JsonRpcClient"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                xrpcli.cmd_pay(make_pay_args())

        output = buf.getvalue()
        self.assertIn("TXHASH123", output)
        self.assertIn("Platform fee:  0.10 USD", output)
        self.assertIn("[p2p:", output)
        self.assertIn("Network fee:   0.00001 XRP (10 drops)", output)

        # Two transactions: the main payment (full amount, to the recipient)
        # and the platform fee (deducted from the sender, to the fee wallet).
        self.assertEqual(mock_submit.call_count, 2)
        sent_payment = mock_submit.call_args_list[0][0][0]
        self.assertEqual(sent_payment.destination, VALID_ADDRESS)
        self.assertEqual(sent_payment.amount, "5000000")
        self.assertEqual(sent_payment.destination_tag, 42)
        fee_payment = mock_submit.call_args_list[1][0][0]
        self.assertEqual(fee_payment.account, "rPayerAddress")
        self.assertEqual(fee_payment.destination, "rFeeCollector")
        self.assertEqual(fee_payment.amount, "100000")

        self.assertEqual(entry["status"], "paid")
        self.assertEqual(entry["tx_hash"], "TXHASH123")
        self.assertEqual(entry["paid_by"], "rPayerAddress")
        self.assertEqual(entry["platform_fee_usd"], "0.10")
        self.assertEqual(entry["platform_fee_drops"], 100000)
        self.assertEqual(entry["network_fee_drops"], 10)
        self.assertEqual(entry["platform_fee_tx_hash"], "FEETXHASH")
        mock_save_requests.assert_called_once()

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests")
    def test_merchant_fee_is_clamped_to_the_minimum_when_collected(
        self,
        mock_load_requests,
        mock_save_requests,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        entry = {
            "status": "pending",
            "address": VALID_ADDRESS,
            "amount": "5",
            "tag": 42,
            "note": None,
            "network": "mainnet",
            "fee_type": "merchant",
        }
        mock_load_requests.return_value = {"abc123": entry}

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        main_response = unittest.mock.Mock()
        main_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "TXHASH123",
        }
        fee_response = unittest.mock.Mock()
        fee_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "FEETXHASH",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=[main_response, fee_response],
        ) as mock_submit, patch("xrpl.clients.JsonRpcClient"):
            xrpcli.cmd_pay(make_pay_args())

        self.assertEqual(mock_submit.call_count, 2)
        fee_payment = mock_submit.call_args_list[1][0][0]
        self.assertEqual(fee_payment.destination, "rFeeCollector")
        # 0.5% of 5 XRP ($5 at rate 1.0) is $0.025, clamped up to the $10 merchant minimum.
        self.assertEqual(fee_payment.amount, "10000000")
        self.assertEqual(entry["platform_fee_tx_hash"], "FEETXHASH")

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests")
    def test_fee_payment_failure_warns_but_does_not_unmark_the_main_payment(
        self,
        mock_load_requests,
        mock_save_requests,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        entry = {
            "status": "pending",
            "address": VALID_ADDRESS,
            "amount": "5",
            "tag": 42,
            "note": None,
            "network": "mainnet",
        }
        mock_load_requests.return_value = {"abc123": entry}

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        main_response = unittest.mock.Mock()
        main_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "TXHASH123",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=[main_response, Exception("connection refused")],
        ), patch("xrpl.clients.JsonRpcClient"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                xrpcli.cmd_pay(make_pay_args())

        self.assertIn("warning: platform fee payment failed to submit", buf.getvalue())
        # The main payment already succeeded, so the request still ends up paid.
        self.assertEqual(entry["status"], "paid")
        self.assertNotIn("platform_fee_tx_hash", entry)
        mock_save_requests.assert_called_once()

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    @patch("xrpcli.save_requests")
    @patch("xrpcli.load_requests")
    def test_does_not_mark_paid_when_result_is_not_success(
        self,
        mock_load_requests,
        mock_save_requests,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        entry = {
            "status": "pending",
            "address": VALID_ADDRESS,
            "amount": "5",
            "tag": 42,
            "note": None,
            "network": "mainnet",
        }
        mock_load_requests.return_value = {"abc123": entry}

        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        mock_response = unittest.mock.Mock()
        mock_response.result = {
            "meta": {"TransactionResult": "tecUNFUNDED_PAYMENT"},
            "hash": "TXHASH123",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait", return_value=mock_response
        ), patch("xrpl.clients.JsonRpcClient"), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_pay(make_pay_args())

        self.assertIn("tecUNFUNDED_PAYMENT", str(ctx.exception))
        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()


class CmdSendStablecoinTests(unittest.TestCase):
    def test_rejects_invalid_destination_address(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(destination="notanaddress"))

        self.assertIn("not a valid XRPL wallet address", str(ctx.exception))

    def test_rejects_unknown_symbol(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(symbol="DOGE"))

        self.assertIn("unknown stablecoin 'DOGE'", str(ctx.exception))
        self.assertIn("USDC", str(ctx.exception))
        self.assertIn("RLUSD", str(ctx.exception))

    def test_symbol_is_case_insensitive(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(symbol="usdc"))

        # Gets past symbol/network validation and fails on the next check instead.
        self.assertIn("XRPL_SECRET", str(ctx.exception))

    def test_rejects_network_with_no_known_issuer(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(network="devnet"))

        self.assertIn("no known USDC issuer for network 'devnet'", str(ctx.exception))

    def test_rejects_invalid_amount(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(amount="not-a-number"))

        self.assertIn("not a valid amount", str(ctx.exception))

    def test_rejects_zero_amount(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(amount="0"))

        self.assertIn("amount must be greater than zero", str(ctx.exception))

    def test_rejects_tag_out_of_range(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(tag=99999999999))

        self.assertIn("--tag must be between 0 and 4294967295", str(ctx.exception))

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_secret_env_var(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("XRPL_SECRET", str(ctx.exception))

    @patch.dict(os.environ, {"XRPL_SECRET": "sEdTest"}, clear=True)
    def test_requires_platform_fee_address_env_var(self):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("PLATFORM_FEE_ADDRESS", str(ctx.exception))

    @patch.dict(os.environ, PAY_ENV, clear=True)
    def test_reports_missing_dependency_when_xrpl_py_not_installed(self):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "xrpl" or name.startswith("xrpl."):
                raise ImportError("No module named 'xrpl'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("xrpl-py", str(ctx.exception))
        self.assertIn("pip install -r requirements.txt", str(ctx.exception))

    @patch.dict(os.environ, {**PAY_ENV, "XRPL_SECRET": "not-a-real-seed"}, clear=True)
    def test_reports_invalid_secret(self):
        with patch(
            "xrpl.wallet.Wallet.from_seed", side_effect=ValueError("bad checksum")
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("invalid XRPL_SECRET", str(ctx.exception))
        self.assertIn("bad checksum", str(ctx.exception))

    @patch.dict(
        os.environ,
        {"XRPL_SECRET": "sEdTest", "PLATFORM_FEE_ADDRESS": "rFeeCollector"},
        clear=True,
    )
    def test_requires_veriff_credentials_env_vars(self):
        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch(
            "xrpl.wallet.Wallet.from_seed", return_value=mock_wallet
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("VERIFF_API_KEY", str(ctx.exception))
        self.assertIn("VERIFF_SHARED_SECRET", str(ctx.exception))

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.create_veriff_session")
    @patch("xrpcli.save_verifications")
    @patch("xrpcli.load_verifications", return_value={})
    def test_first_send_creates_veriff_session_and_blocks(
        self,
        mock_load_verifications,
        mock_save_verifications,
        mock_create_session,
    ):
        mock_create_session.return_value = (
            "sess-new",
            "https://veriff.example/sessions/sess-new",
        )
        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch(
            "xrpl.wallet.Wallet.from_seed", return_value=mock_wallet
        ), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        mock_create_session.assert_called_once_with(
            "rPayerAddress", "test-api-key", "test-shared-secret"
        )
        self.assertIn("has not completed identity verification", str(ctx.exception))
        self.assertIn("https://veriff.example/sessions/sess-new", str(ctx.exception))

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    def test_reports_submission_failure(
        self,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        mock_wallet = unittest.mock.Mock(address="rPayerAddress")

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=Exception("connection refused"),
        ), patch("xrpl.clients.JsonRpcClient"), self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("payment submission failed", str(ctx.exception))
        self.assertIn("connection refused", str(ctx.exception))

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    def test_on_ledger_failure_is_reported_and_does_not_collect_fee(
        self,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        mock_response = unittest.mock.Mock()
        mock_response.result = {
            "meta": {"TransactionResult": "tecNO_LINE"},
            "hash": "TXHASH123",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait", return_value=mock_response
        ) as mock_submit, patch("xrpl.clients.JsonRpcClient"), self.assertRaises(
            SystemExit
        ) as ctx:
            xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        self.assertIn("tecNO_LINE", str(ctx.exception))
        # Only the main payment is attempted -- no fee is collected on a failed send.
        mock_submit.assert_called_once()

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    def test_submits_payment_and_platform_fee_on_success(
        self,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        main_response = unittest.mock.Mock()
        main_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "TXHASH123",
        }
        fee_response = unittest.mock.Mock()
        fee_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "FEETXHASH",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=[main_response, fee_response],
        ) as mock_submit, patch("xrpl.clients.JsonRpcClient"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                xrpcli.cmd_send_stablecoin(make_send_stablecoin_args(amount="25", tag=42))

        output = buf.getvalue()
        self.assertIn("TXHASH123", output)
        self.assertIn("Platform fee:  0.10 USD", output)
        self.assertIn("Network fee:   0.00001 XRP (10 drops)", output)
        self.assertIn("FEETXHASH", output)

        self.assertEqual(mock_submit.call_count, 2)
        sent_payment = mock_submit.call_args_list[0][0][0]
        self.assertEqual(sent_payment.destination, VALID_ADDRESS)
        self.assertEqual(sent_payment.destination_tag, 42)
        self.assertEqual(sent_payment.amount.currency, xrpcli.STABLECOINS["USDC"]["currency"])
        self.assertEqual(sent_payment.amount.issuer, xrpcli.STABLECOINS["USDC"]["issuers"]["mainnet"])
        self.assertEqual(sent_payment.amount.value, "25")

        fee_payment = mock_submit.call_args_list[1][0][0]
        self.assertEqual(fee_payment.account, "rPayerAddress")
        self.assertEqual(fee_payment.destination, "rFeeCollector")
        self.assertEqual(fee_payment.amount, "100000")

    @patch.dict(os.environ, PAY_ENV, clear=True)
    @patch("xrpcli.load_verifications", return_value=APPROVED_VERIFICATION_STORE)
    @patch("xrpcli.rpc_call", return_value=NETWORK_FEE_RESPONSE)
    @patch("xrpcli.fetch_price", return_value=USD_RATE_RESPONSE)
    def test_fee_payment_failure_warns_but_does_not_fail_the_send(
        self,
        mock_fetch_price,
        mock_rpc_call,
        mock_load_verifications,
    ):
        mock_wallet = unittest.mock.Mock(address="rPayerAddress")
        main_response = unittest.mock.Mock()
        main_response.result = {
            "meta": {"TransactionResult": "tesSUCCESS"},
            "hash": "TXHASH123",
        }

        with patch("xrpl.wallet.Wallet.from_seed", return_value=mock_wallet), patch(
            "xrpl.transaction.submit_and_wait",
            side_effect=[main_response, Exception("connection refused")],
        ), patch("xrpl.clients.JsonRpcClient"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                xrpcli.cmd_send_stablecoin(make_send_stablecoin_args())

        output = buf.getvalue()
        self.assertIn("warning: platform fee payment failed to submit", output)
        self.assertIn("Payment sent and validated. tx hash=TXHASH123", output)


class CmdCheckTests(unittest.TestCase):
    def make_pending_entry(self, **overrides):
        entry = {
            "address": VALID_ADDRESS,
            "amount": "5",
            "tag": 42,
            "note": None,
            "network": "mainnet",
            "status": "pending",
        }
        entry.update(overrides)
        return entry

    @patch("xrpcli.load_requests", return_value={})
    def test_rejects_unknown_request_id(self, mock_load_requests):
        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_check(make_check_args(request_id="doesnotexist"))

        self.assertIn("no payment request found", str(ctx.exception))

    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_reports_already_paid_without_network_call(
        self, mock_load_requests, mock_rpc_call
    ):
        mock_load_requests.return_value = {
            "abc123": self.make_pending_entry(status="paid", tx_hash="DEADBEEF")
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_check(make_check_args())

        self.assertIn("already marked paid", buf.getvalue())
        self.assertIn("DEADBEEF", buf.getvalue())
        mock_rpc_call.assert_not_called()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_marks_paid_when_matching_payment_found(
        self, mock_load_requests, mock_rpc_call, mock_save_requests
    ):
        entry = self.make_pending_entry()
        mock_load_requests.return_value = {"abc123": entry}
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "transactions": [make_account_tx_entry()],
            }
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_check(make_check_args())

        output = buf.getvalue()
        self.assertIn("Match found", output)
        self.assertIn("MATCHHASH", output)
        self.assertIn("rPayerAddress", output)

        self.assertEqual(entry["status"], "paid")
        self.assertEqual(entry["tx_hash"], "MATCHHASH")
        self.assertEqual(entry["paid_by"], "rPayerAddress")
        self.assertEqual(entry["verified_via"], "check")
        mock_save_requests.assert_called_once()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_reports_no_match_when_transactions_list_is_empty(
        self, mock_load_requests, mock_rpc_call, mock_save_requests
    ):
        entry = self.make_pending_entry()
        mock_load_requests.return_value = {"abc123": entry}
        mock_rpc_call.return_value = {
            "result": {"status": "success", "transactions": []}
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            xrpcli.cmd_check(make_check_args())

        self.assertIn("No matching payment found yet", buf.getvalue())
        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_ignores_non_payment_transaction_types(
        self, mock_load_requests, mock_rpc_call, mock_save_requests
    ):
        entry = self.make_pending_entry()
        mock_load_requests.return_value = {"abc123": entry}
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "transactions": [make_account_tx_entry(tx_type="EscrowCreate")],
            }
        }

        xrpcli.cmd_check(make_check_args())

        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_ignores_payment_with_wrong_destination_tag(
        self, mock_load_requests, mock_rpc_call, mock_save_requests
    ):
        entry = self.make_pending_entry()
        mock_load_requests.return_value = {"abc123": entry}
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "transactions": [make_account_tx_entry(destination_tag=999)],
            }
        }

        xrpcli.cmd_check(make_check_args())

        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_ignores_payment_with_wrong_amount(
        self, mock_load_requests, mock_rpc_call, mock_save_requests
    ):
        entry = self.make_pending_entry()
        mock_load_requests.return_value = {"abc123": entry}
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "transactions": [make_account_tx_entry(amount="1")],
            }
        }

        xrpcli.cmd_check(make_check_args())

        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()

    @patch("xrpcli.save_requests")
    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_ignores_failed_payment_result(
        self, mock_load_requests, mock_rpc_call, mock_save_requests
    ):
        entry = self.make_pending_entry()
        mock_load_requests.return_value = {"abc123": entry}
        mock_rpc_call.return_value = {
            "result": {
                "status": "success",
                "transactions": [make_account_tx_entry(result="tecPATH_DRY")],
            }
        }

        xrpcli.cmd_check(make_check_args())

        self.assertEqual(entry["status"], "pending")
        mock_save_requests.assert_not_called()

    @patch("xrpcli.rpc_call")
    @patch("xrpcli.load_requests")
    def test_surfaces_friendly_error_for_account_not_found(
        self, mock_load_requests, mock_rpc_call
    ):
        mock_load_requests.return_value = {"abc123": self.make_pending_entry()}
        mock_rpc_call.return_value = {
            "result": {"status": "error", "error": "actNotFound"}
        }

        with self.assertRaises(SystemExit) as ctx:
            xrpcli.cmd_check(make_check_args())

        self.assertIn("account not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
