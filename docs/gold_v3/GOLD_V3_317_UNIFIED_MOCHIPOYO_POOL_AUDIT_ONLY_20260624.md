# GOLD V3 Stage317 — Unified Mochipoyo Pool Audit

## Purpose

Stage316 tested strict delayed confirmations after the original Mochipoyo alerts. It produced 1,486 base events, 129 contextual signals, 88 simulated trades, and 56 fragmented families, but no research pass. The result showed that the confirmation layer was too restrictive to evaluate the method reliably.

Stage317 therefore tests a different interpretation of the documented method: the alert labels are treated as multiple descriptions of one underlying pullback/resumption family rather than as isolated systems.

## Pooled tracks

The following Stage311 Mochipoyo tracks are pooled:

- `MOCHI_EARLY_PULLBACK`
- `MOCHI_HIDDEN_PULLBACK`
- `MOCHI_HTF_RCI_RESUME`
- `MOCHI_ROLL_RETEST`

The pool remains separated by:

- timeframe pair
- direction
- exit profile

## Exact duplicate contract

Rows sharing the same:

- pair
- direction
- exit profile
- entry time

are treated as the same underlying trade only after exact outcome parity is confirmed.

The following values must agree within `1e-12`:

- entry price
- stop price
- target price
- exit price
- risk distance
- spread-adjusted PnL
- spread-adjusted R

The pooled row retains the maximum quality score and records every contributing Mochipoyo track.

## Fixed filters

No new threshold is added after Stage316. Stage317 reuses only the previously declared Stage312 profiles:

- base
- quality at least 7.5
- quality at least 8.0
- quality at least 8.5
- ATR ratio at least 1.0
- round-number-near excluded
- risk no more than 1.25 ATR
- quality 8 and ATR ratio 1
- quality 8 and no round number
- ATR ratio 1 and no round number
- extension from 0.0 to 0.8 ATR
- quality 8 and extension from 0.0 to 0.8 ATR

Exits are limited to 1.25R and 1.50R.

## Selection protocol

- 2024 and 2025 only for selection and ranking
- 2026 display only
- 2026 is not a clean holdout
- Stage311 research gate unchanged
- one position at a time
- no preemption

A positive 2026 result may support a research-watch interpretation but cannot trigger production promotion.

## Outputs

- `stage317_unified_mochipoyo_pool_audit.json`
- `stage317_unified_mochipoyo_all_candidates.csv`
- `stage317_selected_unified_mochipoyo_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage314 prospective contract unchanged
- Stage315 independent research unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
