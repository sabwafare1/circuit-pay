# circuitpay

[![CI](https://github.com/sabwafare1/circuit-pay/actions/workflows/ci.yml/badge.svg)](https://github.com/sabwafare1/circuit-pay/actions/workflows/ci.yml)

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

### stablecoins

Check stablecoin trust line balances (USDC, RLUSD) for a wallet address,
pulled live from the public XRP Ledger network. Tether (USDT) is not
included since Tether does not natively issue USDT on the XRP Ledger.

```
python xrpcli.py stablecoins <address> [--network mainnet|testnet|devnet]
```

- `address` — the XRPL wallet address to check
- `--network` — which XRPL network to query (default: `mainnet`). Each
  stablecoin's issuer address is looked up per network; `devnet` has no
  known issuers for either token.

**Error handling:** the address is validated locally before any network
call is made, so a malformed address never wastes a round trip:

- **Invalid address** — `error: '<address>' is not a valid XRPL wallet
  address`
- **No known issuers for the network** — `error: no known stablecoin
  issuers for network '<network>'`
- **Unreachable network** — `error: failed to reach <endpoint>: <reason>`
  if the XRPL node can't be reached at all
- **Account not found** — `error: account not found on this network (it
  may not exist or has never been funded)` for an address that's
  well-formed but has no ledger entry (XRPL's `actNotFound`)
- **Other RPC errors** — any other `account_lines` error is passed
  through as `error: <message>`
- A stablecoin the address hasn't trusted shows as `no trust line`
  rather than `0`, so you can tell "never opted in" apart from "opted in,
  balance is zero"

**Tests:** `tests/test_xrpcli.py::CmdStablecoinsTests` mocks the RPC call
so no test hits the real network. It checks that: an invalid address is
rejected without ever calling `rpc_call`; a matching trust line prints its
balance while an untrusted stablecoin prints "no trust line"; `devnet` is
rejected up front since it has no known issuers; and an `actNotFound`
error surfaces the friendly "account not found" message.

Live example (run for real against XRPL mainnet — re-checked and still
accurate as of this writing):

```
$ python xrpcli.py stablecoins rMwNibdiFaEzsTaFCG1NnmAM3Rv3vHUy5L
Stablecoin balances for rMwNibdiFaEzsTaFCG1NnmAM3Rv3vHUy5L on mainnet:
  USDC: no trust line
  RLUSD: 0.00204230364
```

#### Setting up a testnet trust line

A fresh wallet has no trust lines at all, so `stablecoins` reports
`no trust line` for everything until you opt in. This CLI has no
`trustset` command of its own, so use `xrpl-py` directly — the same way
the [`pay`](#pay) command's setup steps use it to fund a throwaway
wallet:

1. Fund a throwaway testnet wallet from the public faucet (same command
   as the `pay` section above):

   ```
   python -c "from xrpl.clients import JsonRpcClient; from xrpl.wallet import generate_faucet_wallet; w = generate_faucet_wallet(JsonRpcClient('https://s.altnet.rippletest.net:51234')); print(w.seed, w.address)"
   ```

2. Submit a `TrustSet` transaction for each stablecoin you want to hold,
   using that network's issuer address and currency code from
   `xrpcli.STABLECOINS`:

   ```
   python -c "
   from xrpl.clients import JsonRpcClient
   from xrpl.wallet import Wallet
   from xrpl.models.transactions import TrustSet
   from xrpl.models.amounts import IssuedCurrencyAmount
   from xrpl.transaction import submit_and_wait
   import xrpcli

   client = JsonRpcClient('https://s.altnet.rippletest.net:51234')
   wallet = Wallet.from_seed('sEdT...')  # the seed from step 1

   for symbol, info in xrpcli.STABLECOINS.items():
       tx = TrustSet(
           account=wallet.address,
           limit_amount=IssuedCurrencyAmount(
               currency=info['currency'],
               issuer=info['issuers']['testnet'],
               value='1000000',
           ),
       )
       resp = submit_and_wait(tx, client, wallet)
       print(symbol, '->', resp.result['meta']['TransactionResult'])
   "
   ```

3. Check the balances — they'll show `0` rather than `no trust line`,
   since the trust line now exists but the faucet only funds XRP, not
   stablecoins:

   ```
   python xrpcli.py stablecoins <address> --network testnet
   ```

Live example (run for real against XRPL testnet with a throwaway
faucet-funded wallet — both `TrustSet` transactions landed on-ledger with
`tesSUCCESS`, re-checked and still accurate as of this writing):

```
$ python xrpcli.py stablecoins rhKC5PH4AkqLABbvtjQ48NiTntU8gaCxoq --network testnet
Stablecoin balances for rhKC5PH4AkqLABbvtjQ48NiTntU8gaCxoq on testnet:
  USDC: 0
  RLUSD: 0
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
ID, a shareable `ripple:` payment URI, a scannable QR code rendered right
in the terminal, and an unsigned `Payment` transaction template that a
customer's wallet or tool can use to send that exact payment. The request
is also saved locally (see `pay` below) so it can be looked up and settled
by its ID. Creating the request itself runs entirely offline — no network
call is made.

```
python xrpcli.py request <address> <amount> [--currency XRP|USDC|RLUSD] [--note TEXT] [--tag N] [--network mainnet|testnet|devnet] [--type p2p|merchant]
```

- `address` — the merchant's XRPL wallet address to receive the payment
- `amount` — exact amount to request (up to 6 decimal places for XRP, e.g.
  `12.5`; arbitrary precision for a stablecoin, e.g. `25`)
- `--currency` — `XRP`, `USDC`, or `RLUSD` (case-insensitive, default:
  `XRP`); a stablecoin's issuer address is looked up per network the same
  way [`stablecoins`](#stablecoins) does, so `devnet` has no known issuer
  for either token
- `--note` — a short note describing what the payment is for (embedded as a memo)
- `--tag` — XRPL destination tag to identify this request (a random one is
  generated if omitted); useful for telling apart multiple incoming payments
  to the same address
- `--network` — which XRPL network the request should be paid on (default: `mainnet`)
- `--type` — `p2p` or `merchant` (default: `p2p`); which [platform fee](#platform-fees)
  applies when this request is paid

**QR code:** `request` renders the same `ripple:` URI as a plain-ASCII QR
code printed straight to the terminal (via the optional `qrcode` package
in `requirements.txt`), so a customer can scan it off the screen without
needing the URI typed or pasted anywhere. It's rendered with `#`/space
characters rather than `qrcode`'s own Unicode block art, since that
garbles on a Windows console stuck on a non-UTF-8 codepage. If `qrcode`
isn't installed, `request` still works — everything else it prints is
pure standard library — and just prints a one-line hint to install it
instead of the QR block. For a stablecoin request, the URI (and therefore
the QR code) also carries `currency`/`issuer` query params alongside
`amount`, so a wallet scanning it has everything needed to build the exact
on-ledger payment.

**Request status tracking:** on success, `request` generates a short
random ID (8 hex characters, e.g. `9cc8e589`) that doesn't collide with
any ID already in the store, and writes a new entry to `requests.json`
next to `xrpcli.py` (local only — it's gitignored and never committed):

```json
{
  "address": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
  "amount": "12.5",
  "currency": "XRP",
  "tag": 777,
  "note": "Invoice #42",
  "network": "mainnet",
  "fee_type": "p2p",
  "status": "pending",
  "created_at": "2026-08-16T12:34:56.789012+00:00"
}
```

Every request starts life as `"status": "pending"`. From here, `pay
<request-id>` (see above) is what looks the entry back up, and — only on
a successful on-ledger payment — flips it to `"paid"` and records the
transaction hash, payer address, and paid-at timestamp in the same entry.
A request created before the `currency` field existed has no such key at
all — `pay`/`check` treat that the same as `"currency": "XRP"`, so older
entries in an existing `requests.json` keep working unchanged.

**Error handling:** all validation happens before anything is written to
the local request store, so a rejected request never leaves a partial
entry behind:

- **Invalid address** — `error: '<address>' is not a valid XRPL wallet
  address` (same base58check validation used by `history`/`balance`)
- **Unknown `--currency`** — `error: unknown stablecoin '<currency>', must
  be one of: USDC, RLUSD` (only for a value that isn't `XRP` and isn't a
  known stablecoin)
- **No known issuer for the network** — `error: no known <SYMBOL> issuer
  for network '<network>'` for a stablecoin currency on a network with no
  known issuer (e.g. `devnet`)
- **Invalid amount** — for `XRP`: `error: '<amount>' is not a valid XRP
  amount` for non-numeric input, `error: amount must be greater than zero`
  for zero/negative amounts, or `error: XRP amounts support at most 6
  decimal places` if it has more precision than a drop can represent; for
  a stablecoin: `error: '<amount>' is not a valid amount` or `error:
  amount must be greater than zero` (no decimal-place cap)
- **`--tag` out of range** — `error: --tag must be between 0 and
  4294967295` if given a value outside XRPL's 32-bit destination tag range

**Tests:** `tests/test_xrpcli.py::CmdRequestTests` mocks `load_requests`/
`save_requests` so no test ever touches the real `requests.json` on disk.
It checks that: an invalid address, invalid amount, or out-of-range `--tag`
is rejected before anything is saved; a successful request prints the
expected summary/URI/tx JSON and persists an entry with the right address,
amount, tag, note, and `pending` status; omitting `--note` leaves out the
memo/URI param and the printed "Note:" line; an omitted `--tag` falls back
to a (mocked, deterministic) random tag; a newly generated request ID
never collides with one already present in the store; `--type` defaults to
`p2p` and prints/persists the flat-fee description; `--type merchant`
prints/persists the percentage-fee description instead; a QR code is
printed for the payment URI; and (simulating `qrcode` missing via a
patched `builtins.__import__`) the request still succeeds and prints an
install hint instead of crashing. `tests/test_xrpcli.py::RenderQrAsciiTests`
covers `render_qr_ascii` directly: every printed row is made up only of the
two 2-character tokens it uses for dark/light modules, the rendered grid
contains both, and different input data produces a different grid.

The same test class covers `--currency`: an unknown currency and a
stablecoin currency with no known issuer for the network are both rejected
before saving; a successful `--currency USDC` request prints an
`{amount} USDC` line (no drops), persists `"currency": "USDC"` on the
entry, builds a dict-shaped (`{currency, issuer, value}`) `Amount` in the
unsigned tx template, and includes `currency=`/`issuer=` params in the
URI; and an XRP request (the default) still persists `"currency": "XRP"`.
`tests/test_xrpcli.py::ResolveStablecoinTests` covers the shared
`resolve_stablecoin` helper (also used by [`pay`](#pay), [`check`](#check),
and [`send-stablecoin`](#send-stablecoin)) directly.

Live example (run for real against the local request store — `request`
itself makes no network call, but the request ID below is genuinely
generated, not a placeholder):

```
$ python xrpcli.py request rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh 12.5 --note "Invoice #42" --tag 777
Payment request created:
  Request ID:       710d6acd
  Pay to:           rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
  Amount:           12.5 XRP (12500000 drops)
  Destination tag:  777
  Note:             Invoice #42
  Fee type:         p2p (flat $0.10 fee)

The customer can pay it directly with: xrpcli.py pay 710d6acd

Or give them this to pay manually (paste into a wallet):
  ripple:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh?amount=12.5&dt=777&memo=Invoice+%2342

Or have them scan this to pay:
        ##############  ########    ####  ##    ######          ##  ##############
        ##          ##  ####    ####  ##      ########    ####  ##  ##          ##
        ##  ######  ##  ####  ####  ######  ##    ##    ######      ##  ######  ##
        ##  ######  ##    ####  ##  ##  ####      ##  ##            ##  ######  ##
        ##  ######  ##  ##    ####  ##############    ##    ##  ##  ##  ######  ##
        ##          ##    ##    ##  ####    ##  ####  ########      ##          ##
        ##############  ##  ##  ##  ##  ##  ##  ##  ##  ##  ##  ##  ##############
                          ##    ##  ##                ######  ####
        ##    ############  ####  ################      ##    ##  ##    ##  ######
            ####      ####  ####  ####        ######          ####      ####  ##
        ##  ##  ######  ######  ######      ##      ####  ##########        ##  ##
        ##    ####          ##        ##  ####  ##  ####          ####    ####  ##
              ####  ######    ########        ####  ##      ##      ######    ##
            ##    ##  ####      ##    ##      ##    ##    ##    ##      ##
                  ######    ##      ######    ####      ##  ####  ##  ############
          ##    ####        ##  ######  ##  ######  ####        ##      ##########
            ##  ########    ####  ####  ##  ######  ####  ##############    ##
        ##      ##          ######      ####  ##  ####  ##    ####        ######
        ####      ####  ##        ##  ##      ##  ######  ##  ########  ##  ##  ##
        ##########      ##########              ##  ####  ####  ##    ######
        ##      ##  ##    ####    ##########        ####    ######  ##  ####    ##
        ##    ##  ##    ##  ######    ##    ####  ##              ##  ####  ##
        ####  ##    ####    ##  ##  ####    ##      ####  ##  ##    ##    ##    ##
          ##      ##    ##  ##      ##    ####  ##    ####    ####  ##  ######  ##
        ##    ##########  ####  ##    ############    ####        ####    ##  ####
        ####  ##      ##  ####  ##  ##  ##  ##  ##    ##  ########    ##########
        ####  ##########      ##  ##    ##    ####            ####        ##  ####
        ##                ##  ##    ####    ##      ##      ##    ######  ######
        ##  ####    ##          ##  ##  ##        ####    ##  ############  ##
                        ##  ##  ##            ########  ####    ##      ####  ##
        ##############  ####    ####  ##      ##  ######  ##  ####  ##  ######  ##
        ##          ##  ######    ##      ####  ##  ##  ####  ####      ####  ##
        ##  ######  ##  ####  ########                ####  ################  ##
        ##  ######  ##  ##  ##########  ##  ####    ####  ######  ######  ####  ##
        ##  ######  ##    ######  ##  ######      ######  ######  ####  ####    ##
        ##          ##        ####  ##  ########    ####            ####    ######
        ##############  ##    ######  ##      ####    ##    ##  ####    ##      ##

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
  "710d6acd": {
    "address": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
    "amount": "12.5",
    "currency": "XRP",
    "tag": 777,
    "note": "Invoice #42",
    "network": "mainnet",
    "fee_type": "p2p",
    "status": "pending",
    "created_at": "2026-09-04T06:02:13.355277+00:00"
  }
}
```

A stablecoin request works the same way, with `--currency` and a
per-network issuer/currency code baked into both the URI and the unsigned
tx template (live example, run for real against XRPL testnet):

```
$ python xrpcli.py request rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh 25 --currency USDC --note "Invoice #43" --tag 888 --network testnet
Payment request created:
  Request ID:       9ab638c6
  Pay to:           rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
  Amount:           25 USDC
  Destination tag:  888
  Note:             Invoice #43
  Fee type:         p2p (flat $0.10 fee)

The customer can pay it directly with: xrpcli.py pay 9ab638c6

Or give them this to pay manually (paste into a wallet):
  ripple:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh?amount=25&currency=5553444300000000000000000000000000000000&issuer=rHuGNhqTG32mfmAvWA8hUyWRLV3tCSwKQt&dt=888&memo=Invoice+%2343

Or have them scan this to pay:
  (QR code omitted here for brevity -- rendered the same way as the XRP example above)

Unsigned transaction (for wallets/tools that accept raw XRPL tx JSON):
{
  "TransactionType": "Payment",
  "Destination": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
  "DestinationTag": 888,
  "Amount": {
    "currency": "5553444300000000000000000000000000000000",
    "issuer": "rHuGNhqTG32mfmAvWA8hUyWRLV3tCSwKQt",
    "value": "25"
  },
  "Memos": [
    {
      "Memo": {
        "MemoData": "496E766F69636520233433",
        "MemoFormat": "746578742F706C61696E"
      }
    }
  ]
}

$ cat requests.json
{
  "9ab638c6": {
    "address": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
    "amount": "25",
    "currency": "USDC",
    "tag": 888,
    "note": "Invoice #43",
    "network": "testnet",
    "fee_type": "p2p",
    "status": "pending",
    "created_at": "2026-09-04T06:02:13.522439+00:00"
  }
}
```

### Platform fees

Every request carries a `fee_type` — `p2p` or `merchant`, set via
`request`'s `--type` flag (default `p2p`) — that determines the platform
fee charged when it's paid:

| Type       | Fee                                                        |
| ---------- | ------------------------------------------------------------ |
| `p2p`      | flat $0.10                                                    |
| `merchant` | 0.5% of the amount, clamped to a $10.00 minimum and $5,000.00 maximum |

Fees are USD-denominated but settled in XRP, so `pay` converts them using
the live XRP/USD rate from the same CoinGecko API `price`/`convert` use
(`xrpcli.get_usd_rate`). `pay` prints the requested amount, the platform
fee, and the current XRPL network fee as three separate line items before
submitting, e.g.:

```
Sending 5 XRP from rBFnFXTjvVwp4ar9bYpy9ojcYLgP7bcsha to r4KQHDm9stpeauF1EK986rYB7cuZPSoRBD (tag 404363365) on testnet...
  Amount:        5 XRP (5000000 drops)
  Platform fee:  0.10 USD (~0.099950 XRP) [p2p: flat $0.10 fee]
  Network fee:   0.00001 XRP (10 drops), paid to the XRPL network
```

The network fee is the small, separate cost the XRPL network itself
charges to include the transaction in a ledger (fetched live via the
`fee` RPC method) — it is not part of the platform fee and this tool
never collects it on the platform's behalf.

**Collection is mandatory, and always comes out of the sender's wallet,
never the recipient's.** `pay` requires the `PLATFORM_FEE_ADDRESS`
environment variable (the platform's fee-collection wallet address) the
same way it requires `XRPL_SECRET` — see "Environment setup" below — and
refuses to pay anything without it. The recipient always receives the
exact requested `amount` via the main `Payment`; the platform fee is a
*second*, separate `Payment` sent from the payer's own wallet to
`PLATFORM_FEE_ADDRESS` immediately after the main payment succeeds, and
its hash is recorded on the request entry as `platform_fee_tx_hash`. If
that second transaction fails, `pay` prints a `warning:` rather than
raising — the main payment already succeeded and is not rolled back, so
the request is still marked `paid`; the fee simply needs to be collected
or retried out of band.

`pay` records `platform_fee_usd`, `platform_fee_drops`, and
`network_fee_drops` on the request entry once it settles.

**Tests:** `tests/test_xrpcli.py::CalculatePlatformFeeUsdTests`,
`UsdToDropsTests`, `GetUsdRateTests`, and `FetchNetworkFeeDropsTests`
cover the fee math and lookups in isolation. `CmdPayTests` covers the
integration: `test_requires_platform_fee_address_env_var` asserts `pay`
refuses to run without it; `test_submits_payment_and_marks_request_paid_on_success`
asserts the printed breakdown, that both the main payment (full amount,
to the recipient) and the fee payment (to `PLATFORM_FEE_ADDRESS`, from
the sender) are submitted, and the `platform_fee_*`/`network_fee_drops`
fields saved on the entry; `test_merchant_fee_is_clamped_to_the_minimum_when_collected`
asserts the fee payment amount for a merchant-type request below the
$10 floor; and `test_fee_payment_failure_warns_but_does_not_unmark_the_main_payment`
asserts a failed fee transfer only warns, leaving the already-successful
main payment marked `paid`.

### Identity verification

A wallet must complete [Veriff](https://www.veriff.com/) identity
verification before `pay` will send its first payment. `pay` looks up the
payer's wallet address (derived from `XRPL_SECRET`, not the request) in a
local store, `verifications.json` next to `xrpcli.py` (local only — it's
gitignored and never committed):

- **No record for this address (first payment attempt):** `pay` creates a
  new Veriff verification session via the Veriff Sessions API — passing
  the wallet address as the session's `vendorData`, which is how the
  stored verification result is linked back to that address — saves it
  locally with `"status": "created"`, and **blocks** the payment with an
  error containing the session URL the user needs to complete:

  ```
  error: this wallet has not completed identity verification yet. Complete verification, then retry paying: https://alchemy.veriff.com/v/abc123...
  ```
- **A record exists but isn't `"approved"` yet:** `pay` polls the Veriff
  Decision API for that session, updates the stored status, and blocks
  again unless the decision came back `"approved"`. Before the person has
  finished (or even started) the session, Veriff's decision endpoint
  returns `{"status": "success", "verification": null}` — this tool
  treats that as `"pending"` rather than an error. Once they complete it,
  the status becomes whatever Veriff's decision reports (e.g.
  `"approved"`, `"declined"`, `"resubmission_requested"`).
- **A record exists and is already `"approved"`:** `pay` proceeds
  immediately — no Veriff API call is made, so an already-verified wallet
  pays exactly like it did before this feature existed.

```json
{
  "rBFnFXTjvVwp4ar9bYpy9ojcYLgP7bcsha": {
    "session_id": "abc123",
    "session_url": "https://alchemy.veriff.com/v/abc123",
    "status": "approved",
    "created_at": "2026-08-16T12:00:00+00:00",
    "checked_at": "2026-08-16T12:05:00+00:00"
  }
}
```

**Credentials:** `pay` requires the `VERIFF_API_KEY` and
`VERIFF_SHARED_SECRET` environment variables (see "Environment setup"
below) — the same way it requires `XRPL_SECRET` and
`PLATFORM_FEE_ADDRESS` — and refuses to run without them. Every request
to the Veriff API is signed with an `X-HMAC-SIGNATURE` header
(`xrpcli.veriff_signature`): an HMAC-SHA256 hex digest of the request
body (session creation) or the session ID (decision lookup), keyed with
`VERIFF_SHARED_SECRET`, alongside the `X-AUTH-CLIENT` header carrying
`VERIFF_API_KEY`.

**Error handling:** an unreachable Veriff API surfaces as `error: failed
to reach Veriff API: <reason>`; a response missing the fields this tool
depends on (`verification.id`/`.url` when creating a session, or a
`verification` object with no `status` when checking a decision —
distinct from a `null` `verification`, which means "pending", not
malformed) surfaces as `error: unexpected response from Veriff
when ...: <raw response>` rather than a raw traceback.

**Verified against the real Veriff API** (session creation and decision
polling, sandbox credentials) — not just mocks. That's actually how the
`null`-verification handling above was found: the first version of this
code treated it as a malformed response and raised, until a real session
that hadn't been completed yet returned exactly that shape.

**Tests:** `tests/test_xrpcli.py::VeriffSignatureTests`,
`CreateVeriffSessionTests`, and `FetchVeriffDecisionTests` cover the
signing and HTTP calls in isolation (mocking `urllib.request.urlopen`, so
no test hits the real Veriff API). `EnsurePayerVerifiedTests` covers the
gating logic directly: an already-`approved` record short-circuits
without calling either Veriff endpoint; missing credentials are rejected
before any lookup; a first-time address creates a session and blocks with
its URL; and a pending record is polled and either proceeds (decision
comes back `approved`) or blocks again with the new status (e.g.
`declined`). `CmdPayTests::test_requires_veriff_credentials_env_vars`,
`test_first_payment_creates_veriff_session_and_blocks`, and
`test_blocks_while_pending_verification_is_not_yet_approved` cover the
same gate as `pay` actually exercises it, ahead of any fee calculation or
transaction submission.

### pay

Settle an existing payment request by its ID: looks it up, confirms the
payer's wallet has completed [identity
verification](#identity-verification), then signs and submits the exact
`Payment` transaction (amount, destination, destination tag, note) to the
XRPL network on your behalf, plus the [platform fee](#platform-fees)
computed from the request's `fee_type`. This one **moves real funds** and
requires the `xrpl-py` package (`pip install -r requirements.txt`).

`pay` settles a stablecoin-denominated request (created via
[`request --currency USDC|RLUSD`](#request)) the same way it settles an
XRP one — it reads the request's stored `currency` and builds an
`IssuedCurrencyAmount` payment instead of a plain drops amount when it
isn't `XRP` (falling back to `XRP` for a request created before this field
existed). The [platform fee](#platform-fees) is still always settled in
XRP, using the stablecoin amount directly as its USD value (~1:1 peg) the
same way [`send-stablecoin`](#send-stablecoin) does — see that section for
the full fee-basis writeup.

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

3. Set the platform's fee-collection wallet address in
   `PLATFORM_FEE_ADDRESS`. This is required — `pay` refuses to run
   without it, since [platform fee collection](#platform-fees) is
   mandatory, not optional:

   ```
   # bash / zsh
   export PLATFORM_FEE_ADDRESS=rYourFeeWalletAddress...

   # PowerShell
   $env:PLATFORM_FEE_ADDRESS = "rYourFeeWalletAddress..."

   # Windows cmd
   set PLATFORM_FEE_ADDRESS=rYourFeeWalletAddress...
   ```

4. Set your Veriff API credentials in `VERIFF_API_KEY` and
   `VERIFF_SHARED_SECRET`. This is also required — `pay` refuses to run
   without them, since [identity verification](#identity-verification) is
   mandatory before a wallet's first payment:

   ```
   # bash / zsh
   export VERIFF_API_KEY=your-veriff-api-key
   export VERIFF_SHARED_SECRET=your-veriff-shared-secret

   # PowerShell
   $env:VERIFF_API_KEY = "your-veriff-api-key"
   $env:VERIFF_SHARED_SECRET = "your-veriff-shared-secret"

   # Windows cmd
   set VERIFF_API_KEY=your-veriff-api-key
   set VERIFF_SHARED_SECRET=your-veriff-shared-secret
   ```

   All four steps only need to be done once per shell session. Use a
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
$ export PLATFORM_FEE_ADDRESS=rPlatformFeeWalletAAAAAAAAAAAAAAA
$ export VERIFF_API_KEY=your-veriff-api-key
$ export VERIFF_SHARED_SECRET=your-veriff-shared-secret
$ python xrpcli.py pay c2e32f2d
error: this wallet has not completed identity verification yet. Complete verification, then retry paying: https://alchemy.veriff.com/v/abc123...

# ...customer completes the Veriff flow at that URL, and it comes back approved...

$ python xrpcli.py pay c2e32f2d
Sending 5 XRP from rBFnFXTjvVwp4ar9bYpy9ojcYLgP7bcsha to r4KQHDm9stpeauF1EK986rYB7cuZPSoRBD (tag 404363365) on testnet...
  Amount:        5 XRP (5000000 drops)
  Platform fee:  0.10 USD (~0.099950 XRP) [p2p: flat $0.10 fee]
  Network fee:   0.00001 XRP (10 drops), paid to the XRPL network
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
4. **Missing `PLATFORM_FEE_ADDRESS`** — `error: set the
   PLATFORM_FEE_ADDRESS environment variable to the platform's
   fee-collection wallet address before paying`; [fee collection is
   mandatory](#platform-fees), so `pay` won't run without it
5. **`xrpl-py` not installed** — `error: the 'xrpl-py' package is required
   to send payments. Install it with: pip install -r requirements.txt`
   (only this command needs the dependency; the rest of the CLI still
   works without it)
6. **Invalid secret** — if `Wallet.from_seed` rejects the value, `error:
   invalid XRPL_SECRET: <underlying reason>`

Once the wallet is known (its address comes from the secret, so this is
the earliest point it *can* be checked), `pay` gates on [identity
verification](#identity-verification):

7. **Missing `VERIFF_API_KEY` / `VERIFF_SHARED_SECRET`** — `error: set the
   VERIFF_API_KEY and VERIFF_SHARED_SECRET environment variables to your
   Veriff API credentials before paying`
8. **Wallet not yet verified** — first attempt: `error: this wallet has
   not completed identity verification yet. Complete verification, then
   retry paying: <session url>`. Still pending on a later attempt:
   `error: this wallet's identity verification is not approved yet
   (status: '<status>'). Complete it at: <session url>`

Only after all of that does it look up the [platform fee](#platform-fees)
(requiring the CoinGecko price API and the XRPL `fee` RPC method to both
be reachable — the same `error: failed to reach ...` errors as `price`
and `history` apply here too) and then build and submit the transaction.
Failures from there are also surfaced as clean errors rather than raw
tracebacks:

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
`XRPL_SECRET` set is rejected before any signing is attempted; paying
without `PLATFORM_FEE_ADDRESS` set is likewise rejected up front; a missing
`xrpl-py` install is reported clearly (simulated by patching
`builtins.__import__` to raise `ImportError` for `xrpl` modules, since the
package is actually installed in the test environment); an invalid secret
rejected by `Wallet.from_seed` is reported as `invalid XRPL_SECRET`;
paying without `VERIFF_API_KEY`/`VERIFF_SHARED_SECRET` set is rejected
once the wallet is known but before any Veriff call; a wallet with no
verification record yet has a session created (mocked) and the payment
blocked with the session URL; a `submit_and_wait` failure (e.g. an
unreachable node) is reported as `payment submission failed` and leaves
the request `pending` without saving; a successful submission (for an
already-`approved` wallet — see [Identity
verification](#identity-verification)) submits both the main payment and
the platform-fee payment, marks the request `paid`, records the tx hash,
payer address, and `platform_fee_tx_hash`, and persists the store; a
non-`tesSUCCESS` result on the main payment (e.g. `tecUNFUNDED_PAYMENT`)
raises an error and also leaves the request `pending` without saving; and
a fee payment that fails to submit only prints a `warning:` — the main
payment already succeeded, so the request is still marked `paid`.

Two more cases cover stablecoin-denominated requests specifically: an
entry with no `currency` key at all (predating this field) still pays as
plain XRP; and a `"currency": "USDC"` entry submits an `IssuedCurrencyAmount`
main payment (asserted against `STABLECOINS`' real currency code/issuer)
while the platform fee is computed from the USDC amount directly (not
multiplied by the XRP/USD rate) and still paid in XRP.

### refund

Refund a `paid` request back to whoever paid it: looks it up, confirms
`XRPL_SECRET` belongs to the wallet that actually *received* the original
payment, confirms that wallet has completed [identity
verification](#identity-verification) (the same gate `pay` uses — a wallet
that's already verified doesn't need to verify again), then signs and
submits a `Payment` for the exact original amount and currency back to the
address recorded as `paid_by`. This one **moves real funds** and requires
the `xrpl-py` package, same as `pay`.

```
python xrpcli.py refund <request-id>
```

- `request-id` — the ID printed by `xrpcli.py request` (must currently be `paid`)

Only a full refund of the exact paid amount is supported — there's no
partial-amount option. **The platform fee already collected on the
original payment is not refunded by this command**: it was paid by the
customer as a separate transaction straight to `PLATFORM_FEE_ADDRESS`, and
reversing it would require signing from that wallet, which the merchant
running `refund` doesn't hold the secret for. Recovering a collected
platform fee is between the customer and the platform operator, outside
this tool.

**Request status tracking:** `refund` reads the same `requests.json` entry
that `request` creates and `pay`/`check` settle. On success it updates the
entry in place — leaving the original `tx_hash`/`paid_by` untouched — and
sets a new `status`:

```json
{
  "status": "refunded",
  "tx_hash": "B3737CEDEC9839126D98638E1478330AD9347E38A54ED184DDBC52A84A03435F",
  "paid_by": "rBFnFXTjvVwp4ar9bYpy9ojcYLgP7bcsha",
  "paid_at": "2026-08-17T04:04:10.462975+00:00",
  "refund_tx_hash": "F1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D9E0F1A2",
  "refunded_at": "2026-09-04T12:00:00.000000+00:00"
}
```

`"status": "refunded"` is terminal, same way `"paid"` is final for a
never-paid request: `pay` refuses to pay a refunded request (`error:
request '<id>' was already paid and refunded`), and `check` reports it's
been refunded without ever re-scanning the ledger — important because the
*original* payment is still sitting there on-chain with `tesSUCCESS`, and
without this guard `check` would otherwise find it again and flip the
request back to `"paid"`, erasing the refund.

**Error handling:** checked in order, before ever attempting to sign or submit anything:

1. **Unknown request ID** — `error: no payment request found with id '<id>'`
2. **Already refunded** — `error: request '<id>' was already refunded (tx hash=<hash>)`
3. **Not yet paid** — `error: request '<id>' has not been paid yet, nothing to refund`
   (covers both a `pending` request and any other non-`paid` status)
4. **Missing `XRPL_SECRET`** — `error: set the XRPL_SECRET environment
   variable to the wallet's secret (seed) that received the payment before
   refunding`
5. **`xrpl-py` not installed** / **invalid secret** — same errors as `pay`
6. **Wrong wallet** — `error: XRPL_SECRET belongs to <address>, but this
   request was paid to <merchant-address> -- a refund must be signed by
   the wallet that received the original payment`
7. **Missing Veriff credentials / wallet not yet verified** — same errors
   as [`pay`](#identity-verification), gating on the refunding wallet's
   own address

Once past all of that, submission failures are surfaced the same way as
`pay`: `error: refund submission failed: <reason>` for an unreachable node
or failed submission, and `error: refund failed with result '<code>'` for
a submitted-but-not-`tesSUCCESS` result — in both cases the request is
left `paid` (not `refunded`), so `refund` can simply be retried.

**Tests:** `tests/test_xrpcli.py::CmdRefundTests` covers `refund` end to
end without ever touching the real network or moving funds (the request
store and `xrpl-py`'s `Wallet`/`submit_and_wait`/`JsonRpcClient` are all
mocked, same as `CmdPayTests`). It checks every case listed under "Error
handling" above, plus the success path: a successful refund submits a
`Payment` from the merchant's wallet to the recorded `paid_by` address for
the exact original amount, prints the refund's tx hash, and updates the
entry's `status`/`refund_tx_hash`/`refunded_at` while leaving the original
`tx_hash` intact; a stablecoin-denominated request (`"currency": "USDC"`)
refunds as an `IssuedCurrencyAmount` using that stablecoin's real currency
code/issuer; and a non-`tesSUCCESS` result leaves the request `paid`
without saving. `CmdPayTests::test_rejects_refunded_request` and
`CmdCheckTests::test_reports_refunded_without_network_call_or_remarking_paid`
cover the guards in `pay`/`check` that a refunded request must never be
paid again or silently flipped back to `paid` by a re-scan.

### send-stablecoin

Send USDC or RLUSD directly from your wallet to another address — a
direct wallet-to-wallet transfer, not tied to the `request`/`pay`/`check`
system above (there's no request ID, and nothing is written to
`requests.json`). It's the wallet-to-wallet equivalent of `pay`: same
identity verification gate, same mandatory platform fee, same
`xrpl-py`/environment-variable requirements — just for an issued currency
instead of XRP.

```
python xrpcli.py send-stablecoin <destination> <amount> <USDC|RLUSD> [--tag N] [--network mainnet|testnet|devnet] [--type p2p|merchant]
```

- `destination` — recipient's XRPL wallet address
- `amount` — amount to send, in the stablecoin's own units (e.g. `25`)
- `symbol` — `USDC` or `RLUSD` (case-insensitive)
- `--tag` — XRPL destination tag to include (e.g. an exchange's deposit
  tag); omitted entirely if not given, unlike `request`'s auto-generated
  tag, since there's no local request to later match it against
- `--network` — which XRPL network to send on (default: `mainnet`); each
  stablecoin's issuer address is looked up per network the same way
  [`stablecoins`](#stablecoins) does, and `devnet` has no known issuers
  for either token
- `--type` — `p2p` or `merchant` (default: `p2p`); which [platform
  fee](#platform-fees) applies to this send

**Platform fee:** USDC and RLUSD are pegged ~1:1 to USD, so the send
amount is used directly as its USD value for fee purposes — no price
lookup needed for the amount itself, unlike `pay`'s XRP amount. The fee
itself is still settled in XRP (same as `pay`): computed from the live
XRP/USD rate and sent as a second payment from the sender to
`PLATFORM_FEE_ADDRESS` immediately after the main payment succeeds. If
that second transaction fails, `send-stablecoin` prints a `warning:`
rather than raising — the main payment already succeeded and is not
rolled back — and prints the fee's own tx hash on success (there's no
request entry to record it on, unlike `pay`'s `platform_fee_tx_hash`
field).

**Identity verification:** gated by the same [Veriff
check](#identity-verification) as `pay`, keyed off the sender's wallet
address — a wallet that's already completed verification via `pay`
doesn't need to verify again to use `send-stablecoin`, and vice versa.

**Error handling:** checked in order, before ever attempting to sign or
submit anything:

1. **Invalid destination** — `error: '<address>' is not a valid XRPL
   wallet address`
2. **Unknown symbol** — `error: unknown stablecoin '<symbol>', must be
   one of: USDC, RLUSD`
3. **No known issuer for the network** — `error: no known <SYMBOL> issuer
   for network '<network>'`
4. **Invalid amount** — `error: '<amount>' is not a valid amount` for
   non-numeric input, or `error: amount must be greater than zero` for
   zero/negative amounts
5. **`--tag` out of range** — `error: --tag must be between 0 and
   4294967295`
6. **Missing `XRPL_SECRET`** — `error: set the XRPL_SECRET environment
   variable to your wallet's secret (seed) before sending`
7. **Missing `PLATFORM_FEE_ADDRESS`** — `error: set the
   PLATFORM_FEE_ADDRESS environment variable to the platform's
   fee-collection wallet address before sending`
8. **`xrpl-py` not installed** — same error and fix as `pay`
9. **Invalid secret** — same `error: invalid XRPL_SECRET: <reason>` as `pay`
10. **Missing Veriff credentials / wallet not yet verified** — same errors
    as [`pay`](#identity-verification), gating on the sender's address

Once past all of that, submission failures are surfaced the same way as
`pay` too: an unreachable node or failed submission is `error: payment
submission failed: <reason>`, and a submitted-but-not-`tesSUCCESS` result
(e.g. `tecNO_LINE` if the destination never trusted the currency,
`tecPATH_DRY` if the sender's balance can't reach it) is `error: payment
failed with result '<code>'` — in both cases no platform fee is
attempted, since the main transfer didn't go through.

**Tests:** `tests/test_xrpcli.py::CmdSendStablecoinTests` covers this
without ever touching the real network or moving funds — `xrpl-py`'s
`Wallet`/`submit_and_wait`/`JsonRpcClient` are all mocked. It checks every
case listed under "Error handling" above (including that `symbol` is
case-insensitive), plus: a wallet with no verification record yet has a
session created (mocked) and the send blocked with the session URL; a
successful send submits both the main `IssuedCurrencyAmount` payment (to
the destination, in the requested symbol/network's issuer and currency
code) and the platform-fee payment (in XRP, to `PLATFORM_FEE_ADDRESS`),
printing both tx hashes; a non-`tesSUCCESS` result on the main payment
only attempts that one submission, never the fee; and a fee payment that
fails to submit only prints a `warning:` while the main payment's success
is still reported.

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
the exact requested amount, and a `tesSUCCESS` result. A payment missing
the tag, sent to the wrong address, short/over the exact amount, or not
yet validated is not treated as a match — matching this project's "request
an exact amount" philosophy, and avoiding crediting the wrong customer's
payment to someone else's request on a shared address.

For a stablecoin-denominated request (see [`request
--currency`](#request)), "the exact requested amount" means the ledger
transaction's `Amount` is a `{currency, issuer, value}` object matching
the request's stablecoin and issuer for its network, with `value` equal
to the requested amount (compared numerically, not as a literal string,
since the ledger's own formatting of a value can differ from what was
typed) — an XRP request still matches on a plain drops string, exactly as
before. A request created before the `currency` field existed (no such
key at all) is matched as `XRP`, same as `pay`.

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
correctly ignored rather than matched. For a stablecoin request: a
transaction with the correct `{currency, issuer, value}` `Amount` marks it
paid; one with the wrong issuer, wrong currency, or wrong value is
correctly ignored; and a plain XRP-drops `Amount` doesn't accidentally
match a stablecoin request either.

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

The "no match yet" case reads the same way for a stablecoin request (live
example, checking the USDC request created in [`request`](#request)'s
stablecoin example above, run for real against testnet):

```
$ python xrpcli.py check 9ab638c6
No matching payment found yet for request '9ab638c6' (25 USDC to rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh with tag 888 on testnet).
```
