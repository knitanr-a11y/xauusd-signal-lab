# GOLD V3 Stage320 — Short-Cycle Robustness Audit

## Purpose

Stage319 is a future-only watch and must wait for unseen post-freeze signals. Stage320 is a separate immediate research lane so work does not stop while Stage319 accumulates data.

Stage320 does not add new trading thresholds. It audits only the nine already-fixed Stage318 profiles.

## Source

- Stage318 result JSON
- Stage318 all-profiles trade registry
- exact SHA256 match required

## Selection contract

- 2024 and 2025 only for selection and ranking
- 2026 display only
- 2026 is not used to choose a profile
- no new trading profile is invented
- Stage319 frozen contract is not touched

## Immediate robustness tests

Every fixed Stage318 profile is tested with:

1. year-by-year metrics
2. active-quarter metrics
3. leave-one-active-quarter-out replay
4. rolling six-month windows, requiring at least three trades per window
5. deterministic IID trade bootstrap
6. deterministic active-quarter block bootstrap
7. deterministic trade-order permutation drawdown
8. 95% Wilson interval for win rate

Randomness is fixed with seed 320.

## Robustness gate

A profile passes only when all conditions hold on 2024–2025:

- at least 14 trades
- at least 6 trades in each year
- positive total R in both years
- PF at least 1.50
- positive combined total R
- DD no more than 4R
- largest winner share no more than 35%
- every leave-one-active-quarter-out result remains positive
- at least 90% of eligible rolling six-month windows are positive
- IID bootstrap probability of positive total R at least 90%
- active-quarter block-bootstrap probability of positive total R at least 80%

## Output roles

### Core

Best robust profile with at least 20 selection trades.

### Balanced challenger

Best additional robust profile with at least 16 selection trades, excluding the selected core profile.

### Premium

Highest-win-rate robust profile with at least 14 selection trades.

These are research roles only. None is promoted automatically.

## Outputs

- `stage320_short_cycle_robustness_audit.json`
- `stage320_short_cycle_robustness_leaderboard.csv`
- `stage320_robust_core_trades.csv`
- `stage320_balanced_challenger_trades.csv`
- `stage320_robust_premium_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage317 research watch unchanged
- Stage318 research result unchanged
- Stage315 independent research unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
