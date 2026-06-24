# GOLD V3 Stage325 — Resolved-Only As-Of Membership Router Replay

## Purpose

Stage324 confirmed membership edge rotation inside the fixed Stage322 lane:

`BALANCED_OR_PREMIUM`

- Premium-involved trades dominated 2024–2025.
- Balanced-without-premium trades dominated the 2026 display period.

Stage325 does not permanently prefer either subgroup. It tests fixed online routing policies that use only outcomes from earlier, already-resolved candidate trades.

## Source integrity

Stage325 requires:

- Stage324 status and decision to match
- selected lane exactly `BALANCED_OR_PREMIUM`
- Stage324 timeline SHA256 to match
- 1.0x cost parity within `1e-12`
- no overlapping source positions

## Router groups

Every selected candidate belongs to exactly one disjoint group:

- `PREMIUM_INVOLVED`
- `BALANCED_WITHOUT_PREMIUM`

## Information contract

At each candidate entry:

- only earlier candidates whose exits are already known may contribute to the score
- the current trade outcome is never used
- skipped candidates remain audit-only shadow observations after they resolve
- all source trades are non-overlapping, so prior candidate outcomes are resolved before the next entry

## Fixed policies

No raw market feature is added or tuned.

- static combined baseline
- relative trailing mean R with windows 2, 3, 4, 5
- relative EWMA R with alpha 0.30, 0.50, 0.70 and minimum history 2
- subgroup-positive trailing mean R with windows 2 and 3

All policies use take-all warmup until their required histories exist.

## Selection contract

- 2024 and 2025 only for policy gate and ranking
- 2026 display only
- 2026 cannot select, reject, tune, or rank a policy
- 1.0x and 1.5x spread-cost views are replayed independently using the same fixed policy parameters

## Lead gate

A non-static policy becomes a research lead only when all conditions hold:

- at least 14 selection trades
- at least 6 trades in both 2024 and 2025
- selection win rate at least 75%
- selection PF at least 3.0
- positive selection R
- selection DD no more than 2R
- positive R in both selection years
- under 1.5x cost: at least 14 trades
- under 1.5x cost: win rate at least 75%
- under 1.5x cost: PF at least 3.0
- under 1.5x cost: positive R
- under 1.5x cost: DD no more than 2R

## Outputs

- `stage325_asof_membership_router_replay.json`
- `stage325_asof_membership_router_leaderboard.csv`
- `stage325_selected_asof_router_trades.csv`
- `stage325_selected_asof_router_decision_trace.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage324 result unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
