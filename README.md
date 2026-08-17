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

Live example (run for real against XRPL mainnet — re-checked and this
address's history is unchanged since capture):

```
$ python xrpcli.py history rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh --limit 5
2026-08-16 04:42:10 UTC  EscrowCancel hash=B12968E13A68110199A98D0CC16AFD05DB433BAC842438141A6E0A3773BD056B  result=tesSUCCESS
2026-08-16 04:41:12 UTC  EscrowCreate hash=28BA6E4FB986AC43BD697BB2B45BAAF56DEED73206BD35B02F30BE4311014F1B  result=tesSUCCESS
2026-08-14 06:46:01 UTC  EscrowCancel hash=27F1A9FBB23E4D21860DAEBC788D46C0912D046E1BCDCED13E1C389363102EC4  result=tesSUCCESS
2026-08-14 06:44:41 UTC  EscrowCreate hash=22EC57C0E483EF4B3A173B2859956A323DF801F87B3C2D51037BD6746EC9B7E0  result=tesSUCCESS
2026-08-11 19:05:21 UTC  Payment      hash=AB9D77240EE7414006F979CD8AF43BEAF9EC510F0E99DBFE7A2156BFB7DB56B6  result=tesSUCCESS
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

Live example (run for real against XRPL mainnet — re-checked and still
accurate as of this writing):

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

Live example (run for real against CoinGecko's API — the exact number
will differ whenever you run it, since the price moves continuously; this
was the rate at the moment of capture):

```
$ python xrpcli.py price --currency eur
1 XRP = 0.864481 EUR
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

Live example (run for real against CoinGecko's API — re-checked and the
rate is unchanged since capture, though it can move on future runs):

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

Live example (run for real against the local request store — `request`
itself makes no network call, but the request ID below is genuinely
generated, not a placeholder):

```
$ python xrpcli.py request rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh 12.5 --note "Invoice #42" --tag 777
Payment request created:
  Request ID:       894bc8a7
  Pay to:           rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
  Amount:           12.5 XRP (12500000 drops)
  Destination tag:  777
  Note:             Invoice #42

The customer can pay it directly with: xrpcli.py pay 894bc8a7

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

$ cat requests.json
{
  "894bc8a7": {
    "address": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
    "amount": "12.5",
    "tag": 777,
    "note": "Invoice #42",
    "network": "mainnet",
    "status": "pending",
    "created_at": "2026-08-17T04:27:10.961795+00:00"
  }
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
- `test_reports_submission_failure` — with a mocked `submit_and_wait` that
  raises (e.g. an unreachable node), asserts the same thing one step
  earlier: `status` stays `"pending"` and `save_requests` is never called,
  so a submission that never even reached the ledger can't be mistaken
  for a paid one either
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
It checks every case listed under "Error handling" above, plus the success
path: an unknown request ID is rejected; an already-`paid` request is
rejected (and the error includes its existing tx hash); paying without
`XRPL_SECRET` set is rejected before any signing is attempted; a missing
`xrpl-py` install is reported clearly (simulated by patching
`builtins.__import__` to raise `ImportError` for `xrpl` modules, since the
package is actually installed in the test environment); an invalid secret
rejected by `Wallet.from_seed` is reported as `invalid XRPL_SECRET`; a
`submit_and_wait` failure (e.g. an unreachable node) is reported as
`payment submission failed` and leaves the request `pending` without
saving; a successful submission marks the request `paid`, records the tx
hash and payer address, and persists the store; and a non-`tesSUCCESS`
result (e.g. `tecUNFUNDED_PAYMENT`) raises an error and also leaves the
request `pending` without saving.

### check

Reconcile a payment request against what's actually happened on the
ledger, and mark it paid if a matching payment is found. This closes the
gap `pay` leaves open: most real customers pay by scanning the `ripple:`
QR code from their own wallet rather than running `xrpcli.py pay`, so
`request`/`pay` alone never sees that payment — `check` is what looks for
it after the fact.

```
python xrpcli.py check <request-id> [--limit N]
```

- `request-id` — the ID printed by `xrpcli.py request`
- `--limit` — how many of the merchant's most recent transactions to scan
  for a match (default: `50`)

It scans the merchant address's transaction history and looks for a
`Payment` that matches **all** of: destination address, destination tag,
the exact requested amount (in drops), and a `tesSUCCESS` result. A
payment missing the tag, sent to the wrong address, short/over the exact
amount, or not yet validated is not treated as a match — matching this
project's "request an exact amount" philosophy, and avoiding crediting the
wrong customer's payment to someone else's request on a shared address.

**Request status tracking:** `check` reads and writes the same
`requests.json` entry that `request` creates and `pay` can also settle
(see those sections above for the file's location and the full schema).
On a match it updates the entry the same way a `pay`-driven settlement
does — `status` flips to `"paid"`, and `tx_hash`/`paid_by`/`paid_at` are
filled in from the matched transaction — plus one field only `check` ever
sets:

```json
{
  "status": "paid",
  "tx_hash": "279D6D3424DC83535D6A24A189C67FE488A39B81B73ABC1B26D538E3F8A37F56",
  "paid_by": "r3cnyVdQRJfvprAni4JnkrM1KsdZseijNT",
  "paid_at": "2026-08-17T04:47:16.345116+00:00",
  "verified_via": "check"
}
```

`verified_via: "check"` is how you can tell, after the fact, that a
request was reconciled from a payment made outside this tool (the
customer's own wallet) rather than settled directly by `xrpcli.py pay` —
an entry paid via `pay` has no `verified_via` field at all. Because both
commands write the same `status` field, a request `check` marks paid is
just as final as one `pay` marks paid: running either command again on it
short-circuits on the "already paid" case without touching the network,
and a request left `pending` (no match found yet, or a failed `pay`
attempt) is safe to check or pay again later.

**Error handling:**

- **Unknown request ID** — `error: no payment request found with id
  '<id>'`
- **Already paid** — no error; prints that it's already marked paid (with
  the existing tx hash) and returns without making a network call
- **Unreachable network / RPC errors** — the same `account_tx` error
  handling as `history` (unreachable node, `actNotFound`, or any other RPC
  error passed through)
- **No match found** — not an error; prints a "No matching payment found
  yet" message describing what it was looking for, and leaves the request
  `pending` so it can be checked again later

**Tests:** `tests/test_xrpcli.py::CmdCheckTests` mocks the request store
and the RPC call, so no test hits the real network. It checks that: an
unknown request ID is rejected; an already-paid request short-circuits
before any network call; a matching `Payment` marks the request paid with
the right `tx_hash`/`paid_by`/`verified_via`; an empty transaction list
reports no match without saving; and transactions that are the wrong type,
wrong destination tag, wrong amount, or not `tesSUCCESS` are each
correctly ignored rather than matched.

Live example (run for real against XRPL testnet with two throwaway
faucet-funded wallets — the payer wallet paid the request directly with
`xrpl-py`, entirely independent of `xrpcli.py pay`, simulating a customer
paying from their own wallet via the QR/URI):

```
$ python xrpcli.py request rMYdzDjgcwCjsCiUFDAJycpF7Y39ezgp6A 4 --note "Manual pay test" --network testnet
Payment request created:
  Request ID:       280aec91
  Pay to:           rMYdzDjgcwCjsCiUFDAJycpF7Y39ezgp6A
  Amount:           4 XRP (4000000 drops)
  Destination tag:  2017085237
...

$ python xrpcli.py check 280aec91
No matching payment found yet for request '280aec91' (4 XRP to rMYdzDjgcwCjsCiUFDAJycpF7Y39ezgp6A with tag 2017085237 on testnet).

# ...customer pays 4 XRP to that address/tag directly from their own wallet...

$ python xrpcli.py check 280aec91
Match found - request '280aec91' is now marked paid.
  tx hash: 279D6D3424DC83535D6A24A189C67FE488A39B81B73ABC1B26D538E3F8A37F56
  paid by: r3cnyVdQRJfvprAni4JnkrM1KsdZseijNT

$ python xrpcli.py check 280aec91
Request '280aec91' is already marked paid (tx hash=279D6D3424DC83535D6A24A189C67FE488A39B81B73ABC1B26D538E3F8A37F56).
```
