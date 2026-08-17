# circuitpay

## xrpcli.py

### history

Show transaction history for an XRPL wallet address, pulled live from the
public XRP Ledger network.

```
python xrpcli.py history <address> [--network mainnet|testnet|devnet] [--limit N]
```

- `address` — the XRPL wallet address to query (e.g. `rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh`)
- `--network` — which XRPL network to query (default: `mainnet`)
- `--limit` — maximum number of transactions to show (default: `20`)

Example:

```
$ python xrpcli.py history rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh --limit 5
2026-08-16 04:42:10 UTC  EscrowCancel hash=B12968E13A68110199A98D0CC16AFD05DB433BAC842438141A6E0A3773BD056B  result=tesSUCCESS
2026-08-16 04:41:12 UTC  EscrowCreate hash=28BA6E4FB986AC43BD697BB2B45BAAF56DEED73206BD35B02F30BE4311014F1B  result=tesSUCCESS
...
```

### balance

Check the XRP balance of a wallet address, pulled live from the public XRP
Ledger network.

```
python xrpcli.py balance <address> [--network mainnet|testnet|devnet]
```

- `address` — the XRPL wallet address to check
- `--network` — which XRPL network to query (default: `mainnet`)

**Tests:** `tests/test_xrpcli.py::CmdBalanceTests` mocks the RPC call so no
test hits the real network. It checks that: an invalid address is rejected
without ever calling `rpc_call`; a successful `account_info` response
prints the address, the balance in both XRP and drops, and the network
name; and an `actNotFound` error surfaces the friendly "account not found"
message.

Example:

```
$ python xrpcli.py balance rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh: 56774.125592 XRP (56774125592 drops) on mainnet
```

### price

Check the current XRP price, pulled live from CoinGecko's public price API.

```
python xrpcli.py price [--currency usd]
```

- `--currency` — fiat currency to price XRP in (default: `usd`)

**Currency formatting:** `--currency` is case-insensitive — it's lowercased
before being sent to the API and uppercased in the printed output (`eur`,
`EUR`, and `EuR` all print `... EUR`). The price itself is printed exactly
as returned by the API, with no artificial rounding or padding — currencies
like `jpy` that price XRP as a whole number print without a decimal point
(e.g. `150 JPY`), while others print with full precision (e.g. `0.864225
EUR`).

Example:

```
$ python xrpcli.py price --currency eur
1 XRP = 0.864225 EUR
```

### request

Create a payment request for an exact amount plus a note. Prints a request
ID, a shareable `ripple:` payment URI (paste it into a wallet, or turn it
into a QR code), and an unsigned `Payment` transaction template that a
customer's wallet or tool can use to send that exact payment. The request
is also saved locally (see `pay` below) so it can be looked up and settled
by its ID. Creating the request itself runs entirely offline — no network
call is made.

```
python xrpcli.py request <address> <amount> [--note TEXT] [--tag N] [--network mainnet|testnet|devnet]
```

- `address` — the merchant's XRPL wallet address to receive the payment
- `amount` — exact amount to request, in XRP (up to 6 decimal places, e.g. `12.5`)
- `--note` — a short note describing what the payment is for (embedded as a memo)
- `--tag` — XRPL destination tag to identify this request (a random one is
  generated if omitted); useful for telling apart multiple incoming payments
  to the same address
- `--network` — which XRPL network the request should be paid on (default: `mainnet`)

**Tests:** `tests/test_xrpcli.py::CmdRequestTests` mocks `load_requests`/
`save_requests` so no test ever touches the real `requests.json` on disk.
It checks that: an invalid address, invalid amount, or out-of-range `--tag`
is rejected before anything is saved; a successful request prints the
expected summary/URI/tx JSON and persists an entry with the right address,
amount, tag, note, and `pending` status; omitting `--note` leaves out the
memo/URI param and the printed "Note:" line; an omitted `--tag` falls back
to a (mocked, deterministic) random tag; and a newly generated request ID
never collides with one already present in the store.

Example:

```
$ python xrpcli.py request rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh 12.5 --note "Invoice #42" --tag 777
Payment request created:
  Request ID:       9cc8e589
  Pay to:           rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
  Amount:           12.5 XRP (12500000 drops)
  Destination tag:  777
  Note:             Invoice #42

The customer can pay it directly with: xrpcli.py pay 9cc8e589

Or give them this to pay manually (paste into a wallet, or turn into a QR code):
  ripple:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh?amount=12.5&dt=777&memo=Invoice+%2342

Unsigned transaction (for wallets/tools that accept raw XRPL tx JSON):
{
  "TransactionType": "Payment",
  "Destination": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
  "DestinationTag": 777,
  "Amount": "12500000",
  "Memos": [
    {
      "Memo": {
        "MemoData": "496E766F69636520233432",
        "MemoFormat": "746578742F706C61696E"
      }
    }
  ]
}
```

### pay

Settle an existing payment request by its ID: looks it up, then signs and
submits the exact `Payment` transaction (amount, destination, destination
tag, note) to the XRPL network on your behalf. This one **moves real
funds** and requires the `xrpl-py` package (`pip install -r
requirements.txt`).

```
python xrpcli.py pay <request-id>
```

- `request-id` — the ID printed by `xrpcli.py request`

The payer's wallet secret (seed) must be set in the `XRPL_SECRET`
environment variable — never pass it as a command-line argument, since
that would leak into your shell history and process list. On success, the
request is marked `paid` in the local request store with the resulting
transaction hash, and paying it again is rejected.

Example:

```
$ export XRPL_SECRET=sEdT...           # your wallet's seed, kept out of shell history
$ python xrpcli.py pay 9cc8e589
Sending 12.5 XRP from rPayerAddress... to rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh (tag 777) on mainnet...
Payment sent and validated. tx hash=E1F2...
```

**Tests:** `tests/test_xrpcli.py::CmdPayTests` covers `pay` end to end without
ever touching the real network or moving funds — the request store and the
`xrpl-py` `Wallet`/`submit_and_wait`/`JsonRpcClient` calls are all mocked.
It checks that: an unknown request ID is rejected; an already-`paid`
request is rejected (and the error includes its existing tx hash); paying
without `XRPL_SECRET` set is rejected before any signing is attempted; a
successful submission marks the request `paid`, records the tx hash and
payer address, and persists the store; and a non-`tesSUCCESS` result (e.g.
`tecUNFUNDED_PAYMENT`) raises an error and leaves the request `pending`
without saving.
