#!/usr/bin/env python3
import argparse
import datetime
import json
import urllib.error
import urllib.request

RIPPLE_EPOCH = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)

NETWORKS = {
    "mainnet": "https://xrplcluster.com",
    "testnet": "https://s.altnet.rippletest.net:51234",
    "devnet": "https://s.devnet.rippletest.net:51234",
}


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
        error = result.get("error_message") or result.get("error") or "unknown error"
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

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
