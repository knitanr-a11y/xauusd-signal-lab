# START HERE — BTC ML V1 next chat

Repository: `knitanr-a11y/xauusd-signal-lab`  
Required branch: `main`

## Read first, in this exact order

1. `START_HERE_BTC_ML_V1_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_FRESH_FORWARD_AVAILABILITY_GOLD_FIREWALL_20260729.md`
3. `configs/btc_ml_v1/current_state_20260729.json`
4. `configs/btc_ml_v1/next_action_20260729.json`
5. `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`

Then read only the BTC reproduction and evaluation files listed by the authoritative handoff.

## Current formal state

```text
BTC_FIVE_CANDIDATES_REPRODUCED_FRESH_FORWARD_AVAILABILITY_NOT_YET_VERIFIED
```

Frozen candidates:

- `BTC4_RISK_CAP_400`
- `BTC5_TWO_PIVOT_P2_CLEAN_N_382_786`
- `BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886`
- `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110`
- `BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080`

Exclusive fresh-forward cutoff:

```text
entry_dt > 2026-07-02 02:15:00 UTC
```

## Only next stage

```text
BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY
```

First perform no-write verification inside the allowed BTC scope. If no equivalent current audit exists, implement only the minimal BTC-only FF01 audit defined by the handoff and next-action contract. Stop after producing the availability package.

Do not implement or run fresh performance evaluation, candidate tuning, lot design, new candidate search, collector, loop, dashboard, Discord, MT5 order, live-ready or final-signal work.

## Hard GOLD firewall

During BTC work, do not read, search or modify:

```text
docs/mochipoyo_alert_research/**
config/mochipoyo_alert_research/**
scripts/mochipoyo_alert_research/**
docs/gold_v3/**
docs/gold_ml_v1/**
config/gold_v3/**
config/gold_ml_v1/**
scripts/gold_v3/**
scripts/gold_ml_v1/**
M10W24B
any M10W stage
```

Do not switch to `feature/mochipoyo-alert-research`. Do not touch any GOLD process, collector, BAT, runtime, state, lock, journal, snapshot or checkpoint.

Cleanup commit `0c23fd107680f0f323e956b5f7bbbddc6639243e` must be an ancestor of the working `main`.

This file and the 20260729 handoff/current-state/next-action/firewall override older BTC handoffs when they conflict.
