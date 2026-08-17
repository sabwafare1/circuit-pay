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

Example:

```
$ python xrpcli.py price --currency eur
1 XRP = 0.864225 EUR
```

### request

Create a payment request for an exact amount plus a note. Generates a
shareable `ripple:` payment URI (paste it into a wallet, or turn it into a
QR code) and an unsigned `Payment` transaction template that a customer's
wallet or tool can use to send that exact payment. This runs entirely
offline — no network call is made.

```
python xrpcli.py request <address> <amount> [--note TEXT] [--tag N]
```

- `address` — the merchant's XRPL wallet address to receive the payment
- `amount` — exact amount to request, in XRP (up to 6 decimal places, e.g. `12.5`)
- `--note` — a short note describing what the payment is for (embedded as a memo)
- `--tag` — XRPL destination tag to identify this request (a random one is
  generated if omitted); useful for telling apart multiple incoming payments
  to the same address

Example:

```
$ python xrpcli.py request rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh 12.5 --note "Invoice #42" --tag 777
Payment request created:
  Pay to:           rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh
  Amount:           12.5 XRP (12500000 drops)
  Destination tag:  777
  Note:             Invoice #42

Give this to the customer (paste into a wallet, or turn into a QR code):
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
