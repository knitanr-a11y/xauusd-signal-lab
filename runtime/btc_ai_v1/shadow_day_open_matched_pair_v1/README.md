# BTC AI V1 Day Open Matched-Pair Shadow V1 runtime

This directory is mutable runtime storage. The frozen rule assets live under:

- `scripts/btc_ai_v1/shadow_day_open_matched_pair_v1.py`
- `config/btc_ai_v1/shadow_day_open_matched_pair_v1/`

Do not hand-edit `activation.json`, `current_state.json`, ledgers, or outbox files.
They are written atomically by the runtime.

## Required secret

Set the Discord webhook only as an environment variable:

```powershell
$env:BTC_AI_V1_DAY_OPEN_SHADOW_DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

Never commit the webhook URL.

## Initialization

Initialization creates a no-backfill watermark at the latest fully closed H4
visible in the supplied MT5 CSV files. It is intentionally one-time and refuses
to overwrite an existing activation.

```powershell
python scripts/btc_ai_v1/shadow_day_open_matched_pair_v1.py init `
  --m1 data/mt5/btcusd_m1_latest.csv `
  --m15 data/mt5/btcusd_m15_latest.csv `
  --h4 data/mt5/btcusd_h4_latest.csv `
  --d1 data/mt5/btcusd_d1_latest.csv
```

## Processing

Run after CSV refresh. Entry notifications are first written to a durable outbox
and then sent to Discord. A failed send remains pending and is retried.

```powershell
python scripts/btc_ai_v1/shadow_day_open_matched_pair_v1.py process `
  --m1 data/mt5/btcusd_m1_latest.csv `
  --m15 data/mt5/btcusd_m15_latest.csv `
  --h4 data/mt5/btcusd_h4_latest.csv `
  --d1 data/mt5/btcusd_d1_latest.csv
```

## Safety

- audit-only; no order API exists in this runtime
- exact M1 only; no fallback
- frozen SHA256 verification on every init/process
- rule changes require V2 and a new cutoff
- Stage55 is not read or modified
