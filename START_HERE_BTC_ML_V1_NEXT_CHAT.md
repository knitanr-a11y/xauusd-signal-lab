# START HERE — BTC ML V1 next chat

Repository: `knitanr-a11y/xauusd-signal-lab`  
Authoritative base branch: `main`  
Working branch: `feature/btc-fresh-forward-research`

## Read first, in this exact order

1. `START_HERE_BTC_ML_V1_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_DUAL_TRACK_FF01_M7C_PRESERVED_20260729.md`
3. `configs/btc_ml_v1/current_state_20260729.json`
4. `configs/btc_ml_v1/next_action_20260729.json`
5. `configs/btc_ml_v1/btc_dual_track_scope_20260729.json`
6. `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`

Then read only the BTC reproduction and evaluation files listed by the authoritative V2 handoff.

## Current formal state

```text
BTC_DUAL_TRACK_SEPARATED_FIVE_CANDIDATES_FF01_NEXT_M7C_BACKGROUND_PRESERVED
```

## Two legitimate BTC-related tracks

### Track A — BTC ML V1

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

Track A uses `main` as the authoritative base, but new work is done on `feature/btc-fresh-forward-research`, not directly on `main`.

### Track B — MOCHIPOYO M7C background

`feature/mochipoyo-alert-research` contains a frozen dual-source M7C track for:

- `BTCUSD`
- `XAUUSD`

M7C immutable start:

```text
2026-07-20T14:54:15Z
```

Keep collector, M7C and M8C running unchanged. Do not remove BTCUSD, reset the start, refit formulas, change matching rules or merge this branch into the BTC FF01 branch.

The active M10 candidate/value line remains XAUUSD/GOLD-only. M7C BTC observations do not automatically enter BTC ML V1 or GOLD M10 research.

## Only next stage for Track A

```text
BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY
```

First perform no-write verification inside the allowed BTC ML V1 scope. If no equivalent current audit exists, implement only the minimal BTC-only FF01 audit defined by the V2 handoff and next-action contract. Stop after producing the availability package.

Do not implement or run fresh performance evaluation, candidate tuning, lot design, new candidate search, collector, loop, dashboard, Discord, MT5 order, live-ready or final-signal work.

## Branch and process safety

Use a separate clone or worktree for `feature/btc-fresh-forward-research`.

Do not checkout the existing GOLD/MOCHIPOYO working folder away from `feature/mochipoyo-alert-research`. Do not stop, restart, taskkill, edit or delete its collector, M7C, M8C, M9V+ loops, BATs, runtimes, states, locks, journals, snapshots or checkpoints.

FF01 does not require reading M10W24B or any M10W implementation.

This file and the V2 20260729 handoff/current-state/next-action/dual-track-scope/firewall override older BTC handoffs when they conflict.
