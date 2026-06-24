# GOLD V3 Stage321 — Robust Profile Portfolio Overlap Audit

## Purpose

Stage320 found three robust roles:

- Core: `ATR_STEADY_1_10_TO_1_45`
- Balanced: `CONSENSUS_OR_ATR_STEADY_AND_RANGE`
- Premium: `TREND_FLOW_COMPRESSION_GE_0_95`

Stage321 immediately tests whether these already-fixed profiles work better as a shadow portfolio. It does not wait for Stage319 future signals.

## Source integrity

Stage321 requires:

- Stage320 status and decision to match
- exact SHA256 match for the Stage320 JSON source files
- exact duplicate trade parity within `1e-12`
- no overlapping positions in the unique union

## Fixed logical lanes

No new raw feature threshold is added. Only these fixed combinations are audited:

- `CORE`
- `BALANCED`
- `PREMIUM`
- `CORE_OR_BALANCED`
- `CORE_OR_PREMIUM`
- `BALANCED_OR_PREMIUM`
- `ANY_OF_THREE`
- `AT_LEAST_TWO_OF_THREE`
- `ALL_THREE`

Duplicate trades are counted once.

## Selection contract

- 2024 and 2025 only for selection and ranking
- 2026 display only
- no 2026 result may change candidate eligibility or score

## Immediate shadow gate

A logical lane passes only when all conditions hold on 2024–2025:

- at least 20 trades
- at least 8 trades in each year
- win rate at least 62%
- PF at least 1.50
- positive total R
- DD no more than 4R
- largest winner share no more than 35%
- every leave-one-active-quarter-out result remains positive
- at least 90% positive eligible rolling six-month windows
- IID bootstrap positive-R probability at least 90%
- active-quarter block-bootstrap positive-R probability at least 80%

The selected shadow lane is ranked only with 2024–2025 metrics.

## Outputs

- `stage321_robust_profile_portfolio_overlap_audit.json`
- `stage321_robust_profile_portfolio_leaderboard.csv`
- `stage321_selected_shadow_portfolio_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage317 research watch unchanged
- Stage318 research result unchanged
- Stage320 result unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
