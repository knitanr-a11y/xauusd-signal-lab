# GOLD V3 Stage310 — Stage307 Integrated Portfolio Replay

## Purpose

Evaluate whether the registered Stage307 top ensemble contributes useful, independent trades when added to the existing Stage292/Stage286 safe historical portfolio.

This is an audit-only replay. It does not change the live Stage292 candidate builder or enable any execution path.

## Inputs

Required Stage309 outputs:

- `stage309_stage307_top_candidate_registry.json`
- `stage309_stage307_top_candidate_trades.csv`

Existing portfolio history is auto-discovered below the GOLD V3 output root. Preferred source:

- `gold_v3_stage286_short_selected_portfolio_trades.csv`

Fallback Stage284 selected/balanced portfolio trade names are also recognized. A path can be supplied explicitly with `--existing-portfolio-csv`.

## Input validation

Stage310 requires:

- Stage309 status is registered.
- Stage309 exact parity passed.
- Stage309 trades SHA-256 matches the registry.
- Stage309 trade count remains 92.
- Existing trades provide entry time, exit time and realized PnL, either directly or through entry/exit/direction fields.
- Every trade is resolved and has `exit_dt >= entry_dt`.

When an existing CSV contains multiple portfolio variants, Stage310 prefers `PLUS_STRICT_SAFE`, then `SAFE`, `SELECTED`, or `BALANCED`.

## Fair comparison period

The primary decision uses only the common resolved coverage:

`exit_dt <= min(existing portfolio latest exit, Stage309 latest exit)`

This prevents Stage309 trades after the frozen existing portfolio endpoint from being counted as if the existing strategy had no opportunities during that period.

Full-available metrics are reported separately but are not used for the primary decision.

## One-position replay

Trades are ordered by:

1. `entry_dt`
2. replay priority
3. `candidate_id`

A trade is accepted only when its entry is not earlier than the currently accepted trade's exit. No pre-emption, switching, overlapping positions or outcome-aware selection is permitted.

Three policies are reported:

### EXISTING_FIRST

The frozen existing portfolio wins all same-time conflicts. Stage309 only fills otherwise unused periods.

### CONTRACT_PRIORITY_STAGE309_15

- BASE: 0
- Stage280: 10
- Stage307 top: 15
- Stage281: 20
- Unknown existing additions: 40
- Stage286: 60

This is the primary research policy. Stage307 does not displace an already-open earlier trade.

### BASE_FIRST_STAGE309_BEFORE_ADDITIONS

BASE remains first. Stage307 is evaluated before all non-BASE additions for a diagnostic upper bound.

## Metrics

For baseline, combined portfolio and accepted Stage309 increments:

- trades
- wins/losses/flats
- win rate
- total and average USD PnL
- profit factor
- maximum realized USD drawdown
- yearly 2024/2025/2026 metrics
- accepted/rejected counts by policy
- exact-entry and interval-overlap counts

## Primary gate

The `CONTRACT_PRIORITY_STAGE309_15` policy passes only when all conditions hold on common coverage:

- at least 12 accepted Stage309 trades
- accepted Stage309 win rate at least 52%
- accepted Stage309 PF at least 1.30
- accepted Stage309 total PnL positive
- combined PF at least `max(1.20, baseline PF * 0.95)`
- combined DD no more than baseline DD plus `max(15 USD, baseline DD * 15%)`
- worst Stage309 incremental PnL across 2025 and 2026 above -10 USD

The gate is not relaxed automatically if the candidate fails.

## Outputs

- `stage310_stage307_integrated_portfolio_replay.json`
- `stage310_stage307_integrated_accepted.csv`
- `stage310_stage307_integrated_rejected.csv`

The rejected CSV records the active candidate that blocked each overlapping trade.

## Decision

Pass:

`APPROVE_STAGE307_TOP_FOR_SHADOW_WIRING_DESIGN`

No pass:

`KEEP_STAGE307_TOP_RESEARCH_ONLY`

A pass permits Stage311 to design a frozen audit-only live scorer. It still does not enable production, Discord, MT5 orders or partial close.

## Preserved state

- Stage280 remains blocked.
- Stage281 unchanged.
- Stage286 unchanged.
- Stage292 live candidate pool unchanged.
- final signal unchanged.
- automatic MT5 order OFF.
- Discord OFF.
- partial close OFF.
