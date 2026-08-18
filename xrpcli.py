#!/usr/bin/env python3
import argparse
import datetime
import decimal
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

RIPPLE_EPOCH = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)

NETWORKS = {
    "mainnet": "https://xrplcluster.com",
    "testnet": "https://s.altnet.rippletest.net:51234",
    "devnet": "https://s.devnet.rippletest.net:51234",
}

PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price"

REQUESTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requests.json")

SECRET_ENV_VAR = "XRPL_SECRET"

PLATFORM_FEE_ADDRESS_ENV_VAR = "PLATFORM_FEE_ADDRESS"

FEE_TYPES = ("p2p", "merchant")

# Platform fee schedule, in USD. Percentage fees are clamped to [min, max]
# before being converted to XRP at the current market rate.
P2P_FLAT_FEE_USD = decimal.Decimal("0.10")
MERCHANT_FEE_RATE = decimal.Decimal("0.005")
MERCHANT_FEE_MIN_USD = decimal.Decimal("10.00")
MERCHANT_FEE_MAX_USD = decimal.Decimal("5000.00")

# Ripple's base58 alphabet (different ordering than Bitcoin's).
XRPL_B58_ALPHABET = "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"

RPC_ERROR_MESSAGES = {
    "actNotFound": "account not found on this network (it may not exist or has never been funded)",
    "actMalformed": "malformed account address",
}

# Official issuer addresses per network. Currency codes are the 40-char hex
# encoding required for tickers longer than 3 ASCII characters.
STABLECOINS = {
    "USDC": {
        "currency": "5553444300000000000000000000000000000000",
        "issuers": {
            "mainnet": "rGm7WCVp9gb4jZHWTEtGUr4dd74z2XuWhE",
            "testnet": "rHuGNhqTG32mfmAvWA8hUyWRLV3tCSwKQt",
        },
    },
    "RLUSD": {
        "currency": "524C555344000000000000000000000000000000",
        "issuers": {
            "mainnet": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De",
            "testnet": "rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV",
        },
    },
}


def is_valid_classic_address(address):
    if not address or len(address) < 25 or len(address) > 35:
        return False
    if any(c not in XRPL_B58_ALPHABET for c in address):
        return False

    num = 0
    for char in address:
        num = num * 58 + XRPL_B58_ALPHABET.index(char)
    try:
        decoded = num.to_bytes(25, byteorder="big")
    except OverflowError:
        return False

    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return checksum == expected and payload[0] == 0x00


def xrp_to_drops(amount_str):
    try:
        amount = decimal.Decimal(amount_str)
    except decimal.InvalidOperation:
        raise SystemExit(f"error: '{amount_str}' is not a valid XRP amount")
    if amount <= 0:
        raise SystemExit("error: amount must be greater than zero")

    drops = amount * 1_000_000
    if drops != drops.to_integral_value():
        raise SystemExit("error: XRP amounts support at most 6 decimal places")
    return int(drops)


def drops_to_xrp(drops):
    return decimal.Decimal(drops) / 1_000_000


def usd_to_drops(usd_amount, rate):
    xrp_amount = usd_amount / rate
    return int((xrp_amount * 1_000_000).to_integral_value(rounding=decimal.ROUND_HALF_UP))


def calculate_platform_fee_usd(amount_usd, fee_type):
    if fee_type == "merchant":
        fee = amount_usd * MERCHANT_FEE_RATE
        fee = max(MERCHANT_FEE_MIN_USD, min(fee, MERCHANT_FEE_MAX_USD))
    else:
        fee = P2P_FLAT_FEE_USD
    return fee.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)


def fee_description(fee_type):
    if fee_type == "merchant":
        rate_pct = (MERCHANT_FEE_RATE * 100).normalize()
        return f"{rate_pct}% fee (min ${MERCHANT_FEE_MIN_USD}, max ${MERCHANT_FEE_MAX_USD})"
    return f"flat ${P2P_FLAT_FEE_USD} fee"


def get_usd_rate():
    data = fetch_price("usd")
    price = data.get("ripple", {}).get("usd")
    if price is None:
        raise SystemExit("error: no price data available for usd")
    return decimal.Decimal(str(price))


def fetch_network_fee_drops(endpoint):
    result = rpc_call(endpoint, "fee", {})["result"]
    if result.get("status") != "success":
        code = result.get("error")
        error = RPC_ERROR_MESSAGES.get(code) or result.get("error_message") or code or "unknown error"
        raise SystemExit(f"error: {error}")
    return int(result["drops"]["base_fee"])


def build_payment_uri(address, amount_str, tag, note):
    params = [("amount", amount_str), ("dt", str(tag))]
    if note:
        params.append(("memo", note))
    return f"ripple:{address}?{urllib.parse.urlencode(params)}"


def load_requests():
    if not os.path.exists(REQUESTS_FILE):
        return {}
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_requests(requests_store):
    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests_store, f, indent=2)
        f.write("\n")


def new_request_id(existing):
    while True:
        candidate = secrets.token_hex(4)
        if candidate not in existing:
            return candidate


def rpc_call(endpoint, method, params):
    payload = json.dumps({"method": method, "params": [params]}).encode()
    req = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.URLError as e:
        raise SystemExit(f"error: failed to reach {endpoint}: {e}")


def format_time(ripple_ts):
    if ripple_ts is None:
        return "?"
    return (RIPPLE_EPOCH + datetime.timedelta(seconds=ripple_ts)).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def fetch_price(currency):
    url = f"{PRICE_API_URL}?ids=ripple&vs_currencies={urllib.parse.quote(currency)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.URLError as e:
        raise SystemExit(f"error: failed to reach price API: {e}")


def cmd_price(args):
    currency = args.currency.lower()
    data = fetch_price(currency)
    price = data.get("ripple", {}).get(currency)
    if price is None:
        raise SystemExit(f"error: no price data for currency '{currency}'")
    print(f"1 XRP = {price} {currency.upper()}")


def cmd_convert(args):
    unit = args.unit.lower()
    if unit not in ("xrp", "usd"):
        raise SystemExit(f"error: unit must be 'xrp' or 'usd', got '{args.unit}'")

    try:
        amount = decimal.Decimal(args.amount)
    except decimal.InvalidOperation:
        raise SystemExit(f"error: '{args.amount}' is not a valid amount")
    if amount <= 0:
        raise SystemExit("error: amount must be greater than zero")

    rate = get_usd_rate()

    if unit == "xrp":
        converted = amount * rate
        print(f"{amount} XRP = {converted:.2f} USD (rate: 1 XRP = {rate} USD)")
    else:
        converted = amount / rate
        print(f"{amount} USD = {converted:.6f} XRP (rate: 1 XRP = {rate} USD)")


def cmd_history(args):
    if not is_valid_classic_address(args.address):
        raise SystemExit(
            f"error: '{args.address}' is not a valid XRPL wallet address"
        )

    endpoint = NETWORKS[args.network]
    result = rpc_call(
        endpoint,
        "account_tx",
        {
            "account": args.address,
            "limit": args.limit,
            "binary": False,
        },
    )["result"]

    if result.get("status") != "success":
        code = result.get("error")
        error = RPC_ERROR_MESSAGES.get(code) or result.get("error_message") or code or "unknown error"
        raise SystemExit(f"error: {error}")

    transactions = result.get("transactions", [])
    if not transactions:
        print(f"No transactions found for {args.address} on {args.network}.")
        return

    for entry in transactions:
        tx = entry.get("tx", {})
        meta = entry.get("meta", {})
        tx_result = meta.get("TransactionResult", "?") if isinstance(meta, dict) else "?"
        print(
            f"{format_time(tx.get('date'))}  "
            f"{tx.get('TransactionType', '?'):<12} "
            f"hash={tx.get('hash', '?')}  "
            f"result={tx_result}"
        )


def cmd_balance(args):
    if not is_valid_classic_address(args.address):
        raise SystemExit(
            f"error: '{args.address}' is not a valid XRPL wallet address"
        )

    endpoint = NETWORKS[args.network]
    result = rpc_call(
        endpoint,
        "account_info",
        {
            "account": args.address,
            "ledger_index": "validated",
        },
    )["result"]

    if result.get("status") != "success":
        code = result.get("error")
        error = RPC_ERROR_MESSAGES.get(code) or result.get("error_message") or code or "unknown error"
        raise SystemExit(f"error: {error}")

    drops = int(result["account_data"]["Balance"])
    xrp = decimal.Decimal(drops) / 1_000_000
    print(f"{args.address}: {xrp} XRP ({drops} drops) on {args.network}")


def cmd_stablecoins(args):
    if not is_valid_classic_address(args.address):
        raise SystemExit(
            f"error: '{args.address}' is not a valid XRPL wallet address"
        )

    known_issuers = {}
    for symbol, info in STABLECOINS.items():
        issuer = info["issuers"].get(args.network)
        if issuer is not None:
            known_issuers[(issuer, info["currency"])] = symbol
    if not known_issuers:
        raise SystemExit(
            f"error: no known stablecoin issuers for network '{args.network}'"
        )

    endpoint = NETWORKS[args.network]
    result = rpc_call(
        endpoint,
        "account_lines",
        {
            "account": args.address,
            "ledger_index": "validated",
        },
    )["result"]

    if result.get("status") != "success":
        code = result.get("error")
        error = RPC_ERROR_MESSAGES.get(code) or result.get("error_message") or code or "unknown error"
        raise SystemExit(f"error: {error}")

    balances = {}
    for line in result.get("lines", []):
        symbol = known_issuers.get((line.get("account"), line.get("currency")))
        if symbol is not None:
            balances[symbol] = line.get("balance", "0")

    print(f"Stablecoin balances for {args.address} on {args.network}:")
    for symbol, info in STABLECOINS.items():
        if args.network not in info["issuers"]:
            continue
        if symbol in balances:
            print(f"  {symbol}: {balances[symbol]}")
        else:
            print(f"  {symbol}: no trust line")


def cmd_request(args):
    if not is_valid_classic_address(args.address):
        raise SystemExit(
            f"error: '{args.address}' is not a valid XRPL wallet address"
        )

    drops = xrp_to_drops(args.amount)

    if args.tag is not None and not (0 <= args.tag <= 0xFFFFFFFF):
        raise SystemExit("error: --tag must be between 0 and 4294967295")
    tag = args.tag if args.tag is not None else secrets.randbelow(0xFFFFFFFF) + 1

    tx_template = {
        "TransactionType": "Payment",
        "Destination": args.address,
        "DestinationTag": tag,
        "Amount": str(drops),
    }
    if args.note:
        tx_template["Memos"] = [
            {
                "Memo": {
                    "MemoData": args.note.encode("utf-8").hex().upper(),
                    "MemoFormat": "text/plain".encode("ascii").hex().upper(),
                }
            }
        ]

    uri = build_payment_uri(args.address, args.amount, tag, args.note)

    requests_store = load_requests()
    request_id = new_request_id(requests_store)
    requests_store[request_id] = {
        "address": args.address,
        "amount": args.amount,
        "tag": tag,
        "note": args.note,
        "network": args.network,
        "fee_type": args.fee_type,
        "status": "pending",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_requests(requests_store)

    print("Payment request created:")
    print(f"  Request ID:       {request_id}")
    print(f"  Pay to:           {args.address}")
    print(f"  Amount:           {args.amount} XRP ({drops} drops)")
    print(f"  Destination tag:  {tag}")
    if args.note:
        print(f"  Note:             {args.note}")
    print(f"  Fee type:         {args.fee_type} ({fee_description(args.fee_type)})")
    print()
    print(f"The customer can pay it directly with: xrpcli.py pay {request_id}")
    print()
    print("Or give them this to pay manually (paste into a wallet, or turn into a QR code):")
    print(f"  {uri}")
    print()
    print("Unsigned transaction (for wallets/tools that accept raw XRPL tx JSON):")
    print(json.dumps(tx_template, indent=2))


def cmd_pay(args):
    requests_store = load_requests()
    entry = requests_store.get(args.request_id)
    if entry is None:
        raise SystemExit(f"error: no payment request found with id '{args.request_id}'")
    if entry["status"] == "paid":
        raise SystemExit(
            f"error: request '{args.request_id}' was already paid "
            f"(tx hash={entry.get('tx_hash')})"
        )

    secret = os.environ.get(SECRET_ENV_VAR)
    if not secret:
        raise SystemExit(
            f"error: set the {SECRET_ENV_VAR} environment variable to your wallet's "
            "secret (seed) before paying"
        )

    fee_address = os.environ.get(PLATFORM_FEE_ADDRESS_ENV_VAR)
    if not fee_address:
        raise SystemExit(
            f"error: set the {PLATFORM_FEE_ADDRESS_ENV_VAR} environment variable to the "
            "platform's fee-collection wallet address before paying"
        )

    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.models.transactions import Memo, Payment
        from xrpl.transaction import submit_and_wait
        from xrpl.wallet import Wallet
    except ImportError:
        raise SystemExit(
            "error: the 'xrpl-py' package is required to send payments. "
            "Install it with: pip install -r requirements.txt"
        )

    try:
        wallet = Wallet.from_seed(secret)
    except Exception as e:  # noqa: BLE001 - xrpl doesn't expose a fixed set of decode errors; any failure here means an invalid secret
        raise SystemExit(f"error: invalid {SECRET_ENV_VAR}: {e}")

    drops = xrp_to_drops(entry["amount"])
    network = entry.get("network", "mainnet")
    endpoint = NETWORKS[network]

    fee_type = entry.get("fee_type", "p2p")
    rate = get_usd_rate()
    amount_usd = decimal.Decimal(entry["amount"]) * rate
    platform_fee_usd = calculate_platform_fee_usd(amount_usd, fee_type)
    platform_fee_drops = usd_to_drops(platform_fee_usd, rate)
    network_fee_drops = fetch_network_fee_drops(endpoint)

    memos = None
    if entry.get("note"):
        memos = [
            Memo(
                memo_data=entry["note"].encode("utf-8").hex().upper(),
                memo_format="text/plain".encode("ascii").hex().upper(),
            )
        ]

    payment = Payment(
        account=wallet.address,
        destination=entry["address"],
        amount=str(drops),
        destination_tag=entry.get("tag"),
        memos=memos,
    )

    print(
        f"Sending {entry['amount']} XRP from {wallet.address} to {entry['address']} "
        f"(tag {entry.get('tag')}) on {network}..."
    )
    print(f"  Amount:        {entry['amount']} XRP ({drops} drops)")
    print(
        f"  Platform fee:  {platform_fee_usd:.2f} USD (~{drops_to_xrp(platform_fee_drops)} XRP) "
        f"[{fee_type}: {fee_description(fee_type)}]"
    )
    print(
        f"  Network fee:   {drops_to_xrp(network_fee_drops)} XRP ({network_fee_drops} drops), "
        "paid to the XRPL network"
    )

    client = JsonRpcClient(endpoint)
    try:
        response = submit_and_wait(payment, client, wallet)
    except Exception as e:  # noqa: BLE001 - xrpl-py can raise various network/RPC errors here; any failure means submission didn't succeed
        raise SystemExit(f"error: payment submission failed: {e}")

    result_code = response.result.get("meta", {}).get("TransactionResult")
    tx_hash = response.result.get("hash")

    if result_code != "tesSUCCESS":
        raise SystemExit(f"error: payment failed with result '{result_code}'")

    entry["status"] = "paid"
    entry["tx_hash"] = tx_hash
    entry["paid_by"] = wallet.address
    entry["paid_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry["platform_fee_usd"] = str(platform_fee_usd)
    entry["platform_fee_drops"] = platform_fee_drops
    entry["network_fee_drops"] = network_fee_drops

    # The platform fee is always collected from the sender, as a second
    # transfer out of the same wallet -- the recipient still receives the
    # full requested amount from the main payment above.
    fee_payment = Payment(
        account=wallet.address,
        destination=fee_address,
        amount=str(platform_fee_drops),
    )
    try:
        fee_response = submit_and_wait(fee_payment, client, wallet)
    except Exception as e:  # noqa: BLE001 - a failed fee transfer shouldn't be mistaken for a failed main payment, which already succeeded
        print(f"warning: platform fee payment failed to submit: {e}")
    else:
        fee_result = fee_response.result.get("meta", {}).get("TransactionResult")
        if fee_result == "tesSUCCESS":
            entry["platform_fee_tx_hash"] = fee_response.result.get("hash")
        else:
            print(f"warning: platform fee payment did not succeed (result '{fee_result}')")

    save_requests(requests_store)

    print(f"Payment sent and validated. tx hash={tx_hash}")


def cmd_check(args):
    requests_store = load_requests()
    entry = requests_store.get(args.request_id)
    if entry is None:
        raise SystemExit(f"error: no payment request found with id '{args.request_id}'")

    if entry["status"] == "paid":
        print(
            f"Request '{args.request_id}' is already marked paid "
            f"(tx hash={entry.get('tx_hash')})."
        )
        return

    expected_drops = xrp_to_drops(entry["amount"])
    network = entry.get("network", "mainnet")
    endpoint = NETWORKS[network]

    result = rpc_call(
        endpoint,
        "account_tx",
        {
            "account": entry["address"],
            "limit": args.limit,
            "binary": False,
        },
    )["result"]

    if result.get("status") != "success":
        code = result.get("error")
        error = RPC_ERROR_MESSAGES.get(code) or result.get("error_message") or code or "unknown error"
        raise SystemExit(f"error: {error}")

    for tx_entry in result.get("transactions", []):
        tx = tx_entry.get("tx", {})
        meta = tx_entry.get("meta", {})
        tx_result = meta.get("TransactionResult") if isinstance(meta, dict) else None

        if tx.get("TransactionType") != "Payment":
            continue
        if tx_result != "tesSUCCESS":
            continue
        if tx.get("Destination") != entry["address"]:
            continue
        if tx.get("DestinationTag") != entry.get("tag"):
            continue
        if tx.get("Amount") != str(expected_drops):
            continue

        entry["status"] = "paid"
        entry["tx_hash"] = tx.get("hash")
        entry["paid_by"] = tx.get("Account")
        entry["paid_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry["verified_via"] = "check"
        save_requests(requests_store)

        print(f"Match found - request '{args.request_id}' is now marked paid.")
        print(f"  tx hash: {tx.get('hash')}")
        print(f"  paid by: {tx.get('Account')}")
        return

    print(
        f"No matching payment found yet for request '{args.request_id}' "
        f"({entry['amount']} XRP to {entry['address']} with tag {entry.get('tag')} "
        f"on {network})."
    )


def build_parser():
    parser = argparse.ArgumentParser(prog="xrpcli", description="XRP Ledger CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    history = subparsers.add_parser(
        "history", help="show transaction history for a wallet address"
    )
    history.add_argument("address", help="XRPL wallet address (e.g. rABC...)")
    history.add_argument(
        "--network",
        choices=NETWORKS.keys(),
        default="mainnet",
        help="XRPL network to query (default: mainnet)",
    )
    history.add_argument(
        "--limit",
        type=int,
        default=20,
        help="maximum number of transactions to show (default: 20)",
    )
    history.set_defaults(func=cmd_history)

    balance = subparsers.add_parser(
        "balance", help="check the XRP balance of a wallet address"
    )
    balance.add_argument("address", help="XRPL wallet address (e.g. rABC...)")
    balance.add_argument(
        "--network",
        choices=NETWORKS.keys(),
        default="mainnet",
        help="XRPL network to query (default: mainnet)",
    )
    balance.set_defaults(func=cmd_balance)

    stablecoins = subparsers.add_parser(
        "stablecoins", help="check stablecoin trust line balances (USDC, RLUSD) for a wallet address"
    )
    stablecoins.add_argument("address", help="XRPL wallet address (e.g. rABC...)")
    stablecoins.add_argument(
        "--network",
        choices=NETWORKS.keys(),
        default="mainnet",
        help="XRPL network to query (default: mainnet)",
    )
    stablecoins.set_defaults(func=cmd_stablecoins)

    price = subparsers.add_parser("price", help="check the current XRP price")
    price.add_argument(
        "--currency",
        default="usd",
        help="fiat currency to price XRP in (default: usd)",
    )
    price.set_defaults(func=cmd_price)

    convert = subparsers.add_parser(
        "convert", help="convert an amount between XRP and USD"
    )
    convert.add_argument("amount", help="amount to convert")
    convert.add_argument("unit", help="unit of the amount to convert from: xrp or usd")
    convert.set_defaults(func=cmd_convert)

    request = subparsers.add_parser(
        "request", help="create a payment request for a customer to pay"
    )
    request.add_argument("address", help="merchant's XRPL wallet address to receive payment")
    request.add_argument("amount", help="exact amount to request, in XRP (e.g. 12.5)")
    request.add_argument(
        "--note", default=None, help="a short note describing what the payment is for"
    )
    request.add_argument(
        "--tag",
        type=int,
        default=None,
        help="XRPL destination tag to identify this request (random if omitted)",
    )
    request.add_argument(
        "--network",
        choices=NETWORKS.keys(),
        default="mainnet",
        help="XRPL network the request should be paid on (default: mainnet)",
    )
    request.add_argument(
        "--type",
        dest="fee_type",
        choices=FEE_TYPES,
        default="p2p",
        help=(
            "transaction type for platform fee purposes: 'p2p' (flat $0.10) or "
            "'merchant' (0.5 percent, min $10, max $5000) (default: p2p)"
        ),
    )
    request.set_defaults(func=cmd_request)

    pay = subparsers.add_parser(
        "pay", help="pay an existing payment request by its ID"
    )
    pay.add_argument("request_id", help="the request ID printed by 'xrpcli.py request'")
    pay.set_defaults(func=cmd_pay)

    check = subparsers.add_parser(
        "check",
        help="check whether a payment request has been paid, and reconcile it if so",
    )
    check.add_argument("request_id", help="the request ID printed by 'xrpcli.py request'")
    check.add_argument(
        "--limit",
        type=int,
        default=50,
        help="how many recent transactions on the merchant's account to scan (default: 50)",
    )
    check.set_defaults(func=cmd_check)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
