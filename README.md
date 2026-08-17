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

**Error handling:** the address is validated locally before any network
call is made, so a malformed address never wastes a round trip:

- **Invalid address** — `error: '<address>' is not a valid XRPL wallet
  address`
- **Unreachable network** — `error: failed to reach <endpoint>: <reason>`
  if the XRPL node can't be reached at all
- **Account not found** — `error: account not found on this network (it
  may not exist or has never been funded)` for an address that's
  well-formed but has no ledger entry (XRPL's `actNotFound`)
- **Other RPC errors** — any other `account_tx` error is passed through as
  `error: <message>`

**Tests:** `tests/test_xrpcli.py::CmdHistoryTests` mocks the RPC call so no
test hits the real network. It checks that: an invalid address is rejected
without ever calling `rpc_call`; a successful `account_tx` response prints
each transaction's type, hash, and result; an empty transaction list
prints a "No transactions found" message instead of nothing; and an
`actNotFound` error surfaces the friendly "account not found" message.

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

**Error handling:** the address is validated locally before any network
call is made, so a malformed address never wastes a round trip:

- **Invalid address** — `error: '<address>' is not a valid XRPL wallet
  address`
- **Unreachable network** — `error: failed to reach <endpoint>: <reason>`
  if the XRPL node can't be reached at all
- **Account not found** — `error: account not found on this network (it
  may not exist or has never been funded)` for an address that's
  well-formed but has no ledger entry (XRPL's `actNotFound`)
- **Other RPC errors** — any other `account_info` error is passed through
  as `error: <message>`

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

**Error handling:**

- **Unreachable API** — `error: failed to reach price API: <reason>` if
  CoinGecko can't be reached at all
- **Unrecognized currency** — `error: no price data for currency
  '<currency>'` if the API responds but has no price for that currency
  code (e.g. a typo, or a currency CoinGecko doesn't track)

**Currency formatting:** `--currency` is case-insensitive — it's lowercased
before being sent to the API and uppercased in the printed output (`eur`,
`EUR`, and `EuR` all print `... EUR`). The price itself is printed exactly
as returned by the API, with no artificial rounding or padding — currencies
like `jpy` that price XRP as a whole number print without a decimal point
(e.g. `150 JPY`), while others print with full precision (e.g. `0.864225
EUR`).

**Tests:** `tests/test_xrpcli.py::CmdPriceTests` mocks `fetch_price` so no
test hits the real API. It checks that: a successful lookup prints the
price and currency; `--currency` is lowercased before being sent to
`fetch_price` regardless of input case (`EUR`, `UsD`); an unrecognized
currency raises a clear error; several currency codes (`jpy`, `gbp`, `btc`)
uppercase correctly in the output; and an integer price (e.g. `150` for
`jpy`) prints without a spurious `.0`.

Example:

```
$ python xrpcli.py price --currency eur
1 XRP = 0.864225 EUR
```

### convert

Convert an amount between XRP and USD, using the live rate from
CoinGecko's public price API.

```
python xrpcli.py convert <amount> <xrp|usd>
```

- `amount` — the amount to convert (must be a positive number)
- `unit` — the unit of `amount`: `xrp` or `usd` (case-insensitive);
  converts to the other unit

**Error handling:** `unit` and `amount` are both validated locally before
`fetch_price` is ever called, so a bad argument never wastes a network
call:

- **Invalid unit** — `error: unit must be 'xrp' or 'usd', got '<unit>'`
- **Invalid amount** — `error: '<amount>' is not a valid amount` for
  non-numeric input, or `error: amount must be greater than zero` for
  zero/negative amounts
- **Unreachable API / no rate available** — the same `fetch_price` errors
  as `price` (`error: failed to reach price API: <reason>`), plus `error:
  no price data available for usd` if the API responds without a USD rate

**Tests:** `tests/test_xrpcli.py::CmdConvertTests` mocks `fetch_price` so
no test hits the real API. It checks that: converting XRP to USD and USD
to XRP both produce the expected amount and print the rate used; `unit` is
case-insensitive (`XRP` works the same as `xrp`); an invalid unit, a
non-numeric amount, and a zero/negative amount are all rejected before
`fetch_price` is ever called; and a response with no USD price available
raises a clear error.

Example:

```
$ python xrpcli.py convert 100 xrp
100 XRP = 100.10 USD (rate: 1 XRP = 1.001 USD)
$ python xrpcli.py convert 50 usd
50 USD = 49.950050 XRP (rate: 1 XRP = 1.001 USD)
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

**Request status tracking:** on success, `request` generates a short
random ID (8 hex characters, e.g. `9cc8e589`) that doesn't collide with
any ID already in the store, and writes a new entry to `requests.json`
next to `xrpcli.py` (local only — it's gitignored and never committed):

```json
{
  "address": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
  "amount": "12.5",
  "tag": 777,
  "note": "Invoice #42",
  "network": "mainnet",
  "status": "pending",
  "created_at": "2026-08-16T12:34:56.789012+00:00"
}
```

Every request starts life as `"status": "pending"`. From here, `pay
<request-id>` (see above) is what looks the entry back up, and — only on
a successful on-ledger payment — flips it to `"paid"` and records the
transaction hash, payer address, and paid-at timestamp in the same entry.

**Error handling:** all validation happens before anything is written to
the local request store, so a rejected request never leaves a partial
entry behind:

- **Invalid address** — `error: '<address>' is not a valid XRPL wallet
  address` (same base58check validation used by `history`/`balance`)
- **Invalid amount** — `error: '<amount>' is not a valid XRP amount` for
  non-numeric input, `error: amount must be greater than zero` for
  zero/negative amounts, or `error: XRP amounts support at most 6 decimal
  places` if it has more precision than a drop can represent
- **`--tag` out of range** — `error: --tag must be between 0 and
  4294967295` if given a value outside XRPL's 32-bit destination tag range

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

**Request status tracking:** every request lives in `requests.json` next
to `xrpcli.py` (local only — it's gitignored and never committed, since
it can contain addresses and payment notes). `request` writes a new entry
with `"status": "pending"`; `pay` reads it, and only on a successful
`tesSUCCESS` submission updates it in place:

```json
{
  "status": "paid",
  "tx_hash": "B3737CEDEC9839126D98638E1478330AD9347E38A54ED184DDBC52A84A03435F",
  "paid_by": "rBFnFXTjvVwp4ar9bYpy9ojcYLgP7bcsha",
  "paid_at": "2026-08-17T04:04:10.462975+00:00"
}
```

`status` is the source of truth `pay` checks before doing anything else —
a `pending` request can be paid, a `paid` one is rejected (see "Already
paid" below), and a request left `pending` after a failed on-ledger result
(see "Error handling" below) can simply be retried with `pay` again.

**Tests for status tracking:** three `CmdPayTests` cases in
`tests/test_xrpcli.py` exercise this lifecycle directly, all without
touching the real `requests.json` or the network (`load_requests` /
`save_requests` and the `xrpl-py` calls are mocked):

- `test_submits_payment_and_marks_request_paid_on_success` — after a mocked
  `submit_and_wait` returns `tesSUCCESS`, asserts the in-memory entry's
  `status` becomes `"paid"` and `tx_hash`/`paid_by` are set to the values
  from the response, and that `save_requests` is called exactly once to
  persist it
- `test_does_not_mark_paid_when_result_is_not_success` — with a mocked
  `tecUNFUNDED_PAYMENT` result, asserts the entry's `status` is left
  unchanged as `"pending"` and `save_requests` is **not** called, so a
  failed payment never gets recorded as paid
- `test_rejects_already_paid_request` — seeds the store with an entry
  whose `status` is already `"paid"`, and asserts `pay` raises before
  doing anything else, with the error message including the existing
  `tx_hash`

**Environment setup:** `pay` is the only command with extra setup, since
it's the only one that actually signs and submits a transaction.

1. Install the `xrpl-py` dependency (the rest of the CLI stays
   dependency-free and doesn't need this):

   ```
   pip install -r requirements.txt
   ```

2. Set the payer's wallet secret (seed) in the `XRPL_SECRET` environment
   variable. **Never pass it as a command-line argument** — a CLI arg
   lands in your shell history and is visible to other processes on the
   machine, while an environment variable set for the current session
   isn't:

   ```
   # bash / zsh
   export XRPL_SECRET=sEdT...

   # PowerShell
   $env:XRPL_SECRET = "sEdT..."

   # Windows cmd
   set XRPL_SECRET=sEdT...
   ```

   Both steps only need to be done once per shell session. Use a
   throwaway testnet wallet's seed while trying this out, not a mainnet
   one — `xrpl-py` can generate and fund one for free from the public
   XRPL testnet faucet:

   ```
   python -c "from xrpl.clients import JsonRpcClient; from xrpl.wallet import generate_faucet_wallet; w = generate_faucet_wallet(JsonRpcClient('https://s.altnet.rippletest.net:51234')); print(w.seed, w.address)"
   ```

Live example (run against XRPL testnet with two throwaway faucet-funded
wallets — no real funds involved, and the transaction really landed
on-ledger with `tesSUCCESS`):

```
$ python xrpcli.py request r4KQHDm9stpeauF1EK986rYB7cuZPSoRBD 5 --note "Invoice #42" --network testnet
Payment request created:
  Request ID:       c2e32f2d
  Pay to:           r4KQHDm9stpeauF1EK986rYB7cuZPSoRBD
  Amount:           5 XRP (5000000 drops)
  Destination tag:  404363365
  Note:             Invoice #42
...

$ export XRPL_SECRET=sEdVCt7SStTpySutToQw73kPZgDMguA   # a throwaway testnet wallet's seed
$ python xrpcli.py pay c2e32f2d
Sending 5 XRP from rBFnFXTjvVwp4ar9bYpy9ojcYLgP7bcsha to r4KQHDm9stpeauF1EK986rYB7cuZPSoRBD (tag 404363365) on testnet...
Payment sent and validated. tx hash=B3737CEDEC9839126D98638E1478330AD9347E38A54ED184DDBC52A84A03435F

$ python xrpcli.py history r4KQHDm9stpeauF1EK986rYB7cuZPSoRBD --network testnet --limit 1
2026-08-17 04:04:10 UTC  Payment      hash=B3737CEDEC9839126D98638E1478330AD9347E38A54ED184DDBC52A84A03435F  result=tesSUCCESS
```

**Error handling:** `pay` checks things in order, before ever attempting to
sign or submit anything:

1. **Unknown request ID** — `error: no payment request found with id '<id>'`
2. **Already paid** — `error: request '<id>' was already paid (tx hash=<hash>)`,
   so the same request can never be paid twice
3. **Missing `XRPL_SECRET`** — `error: set the XRPL_SECRET environment
   variable to your wallet's secret (seed) before paying`
4. **`xrpl-py` not installed** — `error: the 'xrpl-py' package is required
   to send payments. Install it with: pip install -r requirements.txt`
   (only this command needs the dependency; the rest of the CLI still
   works without it)
5. **Invalid secret** — if `Wallet.from_seed` rejects the value, `error:
   invalid XRPL_SECRET: <underlying reason>`

Only after all of that does it build and submit the transaction. Failures
from there are also surfaced as clean errors rather than raw tracebacks:

- **Submission/network failure** (unreachable node, unfunded sender
  account, bad autofill, etc.) — `error: payment submission failed:
  <underlying xrpl-py exception>`
- **On-ledger failure** — if the transaction is submitted but doesn't
  validate with `tesSUCCESS` (e.g. `tecUNFUNDED_PAYMENT`,
  `tecNO_DST_INSUFF_XRP`) — `error: payment failed with result '<code>'`.
  In this case the request is **left `pending`**, not marked paid, so it
  can be retried.

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
