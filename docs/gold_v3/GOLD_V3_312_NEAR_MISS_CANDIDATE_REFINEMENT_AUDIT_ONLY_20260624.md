# GOLD V3 Stage312 — Near-Miss Candidate Refinement

## Purpose

Refine only the strongest Stage311 near-miss families. Stage312 does not search for historical portfolio files and does not rerun the full signal-generation grid.

## Fixed source families

- `M5_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_5`
- `M15_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_5`
- `M15_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_25`
- `M5_H4|MOCHI_EARLY_PULLBACK|SHORT|RR1_5`
- `M5_H4|SWEEP_RECLAIM_REVERSAL|SHORT|STRUCT_TARGET`

These were selected because Stage311 showed only one principal failure or a useful diagnostic pattern. No other families are added after observing Stage312 output.

## Fixed filter grid

The filter profiles are frozen in code before the Stage312 run:

- no filter
- quality score at least 7.5
- quality score at least 8.0
- quality score at least 8.5
- ATR ratio at least 1.0
- exclude round-number-near entries
- risk distance no more than 1.25 ATR
- quality at least 8.0 plus ATR ratio at least 1.0
- quality at least 8.0 plus no round-number-near entry
- ATR ratio at least 1.0 plus no round-number-near entry
- extension from EMA20 between 0 and 0.8 ATR
- quality at least 8.0 plus extension between 0 and 0.8 ATR

No time-of-day filter is tested because MT5 server-time interpretation would require a separate contract.

## Selection and gate

Selection uses 2024 and 2025 only. The Stage311 gate is not weakened:

- at least 30 combined trades
- at least 10 trades in each year
- PF at least 1.10 in each year
- positive R in each year
- combined PF at least 1.25
- combined positive R
- combined maximum drawdown no more than 10R
- largest winner share no more than 40%

## 2026 treatment

2026 is an audit stress check only. It is explicitly not a pristine holdout because Stage311 already displayed the 2026 outcomes.

A Stage312 formal pass therefore creates only a research refinement lead. It does not permit production or shadow promotion. A separate rolling-window and regime-stability stage is still required.

## Important interpretation

The Stage311 M5/H4 sweep-reclaim SHORT structural-target family showed strong 2024–2025 performance but nine consecutive losses in 2026. Stage312 reports it but does not treat it as robust merely because it passes the earlier-year gate.

The principal refinement target is the M5/H4 hidden-pullback LONG family, whose Stage311 weakness was drawdown rather than lack of edge.

## Outputs

- `stage312_near_miss_candidate_refinement.json`
- `stage312_selected_refined_candidate_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage280 remains blocked
- Stage307 top remains unchanged as a registered research candidate
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
