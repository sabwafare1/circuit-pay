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
