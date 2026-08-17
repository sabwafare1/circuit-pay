#!/usr/bin/env python3
import argparse
import datetime
import decimal
import hashlib
import json
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

# Ripple's base58 alphabet (different ordering than Bitcoin's).
XRPL_B58_ALPHABET = "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"

RPC_ERROR_MESSAGES = {
    "actNotFound": "account not found on this network (it may not exist or has never been funded)",
    "actMalformed": "malformed account address",
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


def build_payment_uri(address, amount_str, tag, note):
    params = [("amount", amount_str), ("dt", str(tag))]
    if note:
        params.append(("memo", note))
    return f"ripple:{address}?{urllib.parse.urlencode(params)}"


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

    print("Payment request created:")
    print(f"  Pay to:           {args.address}")
    print(f"  Amount:           {args.amount} XRP ({drops} drops)")
    print(f"  Destination tag:  {tag}")
    if args.note:
        print(f"  Note:             {args.note}")
    print()
    print("Give this to the customer (paste into a wallet, or turn into a QR code):")
    print(f"  {uri}")
    print()
    print("Unsigned transaction (for wallets/tools that accept raw XRPL tx JSON):")
    print(json.dumps(tx_template, indent=2))


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
    request.set_defaults(func=cmd_request)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
