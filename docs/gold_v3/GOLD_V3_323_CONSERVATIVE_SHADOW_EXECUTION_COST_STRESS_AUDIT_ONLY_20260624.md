# GOLD V3 Stage323 — Conservative Shadow Execution Cost Stress Audit

## Purpose

Stage322 selected the fixed shadow lane:

`BALANCED_OR_PREMIUM`

Stage323 does not change that lane and does not invent a new entry filter. It immediately tests whether the exact selected trades remain viable when spread costs are materially worse than the recorded baseline.

## Source integrity

Stage323 requires:

- Stage322 status and decision to match
- selected lane exactly `BALANCED_OR_PREMIUM`
- selected trade CSV SHA256 to match Stage322
- rebuilt 1.0x spread PnL and R to match the stored values within `1e-12`
- no overlapping positions

## Fixed stress scenarios

The cost formula is:

`stress_pnl = gross_pnl - cost_multiplier * entry_spread_price`

Fixed multipliers:

- 1.0x
- 1.25x
- 1.5x
- 2.0x
- 3.0x

No raw market-feature threshold is tuned.

## Selection contract

- 2024 and 2025 only for the execution-stress gate
- 2026 display only
- 2026 cannot change the gate result

## Execution-stress gate

The selected shadow is supported only when all conditions hold:

- exact 1.0x cost parity
- at 1.5x cost: PF at least 1.50
- at 1.5x cost: positive total R
- at 1.5x cost: DD no more than 4R
- at 1.5x cost: both 2024 and 2025 remain positive
- at 2.0x cost: PF at least 1.25
- at 2.0x cost: positive total R
- at 3.0x cost: positive total R
- largest winner share no more than 35%

## Outputs

- `stage323_conservative_shadow_execution_cost_stress_audit.json`
- `stage323_execution_cost_stress_scenarios.csv`
- `stage323_execution_cost_stressed_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage322 result unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
