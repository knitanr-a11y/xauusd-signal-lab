# GOLD V3 53 pending-to-closed shadow trade adjudication ledger audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_53_PENDING_TO_CLOSED_SHADOW_TRADE_ADJUDICATION_LEDGER_SPEC_READY_AUDIT_ONLY`

## Purpose

Build audit-only ledgers for:

1. `pending_shadow_trade_ledger`
2. `closed_shadow_trade_ledger`

Stage53 reads the Stage52 selected trade ledger, converts selected trades into pending shadow trades, then independently adjudicates them using M5 candles and compares the resulting closed shadow trade ledger against Stage52 selected trade outcomes.

Stage53 does **not** implement live trading, does **not** send signals, and does **not** change candidate or gate logic.

## Frozen upstream contract

Stage53 must preserve:

- `htf_asof = closed`
- OPEN asof prohibited
- full Stage45 base + HV sibling candidate pool retained
- no manual candidate demotion/removal
- strict rolling health gate unchanged
- all candidates virtually monitored
- selected trades from Stage52 only

## Adjudication contract

For each selected Stage52 trade:

- create `pending_shadow_trade_ledger` row
- use `entry_dt`, `entry_price`, `tp_usd`, `sl_usd`, and `horizon_m15`
- convert horizon to M5 bars by `horizon_m15 * 3`
- evaluate M5 candles strictly after entry time
- TP price: `entry_price + tp_usd`
- SL price: `entry_price - sl_usd`
- if TP and SL hit on the same M5 bar, SL wins
- if neither TP nor SL hits by timeout, outcome is TIMEOUT at last available horizon M5 close
- complete horizon only

This reproduces Stage45's long-side USD-price adjudication behavior.

## Required upstream artifacts

- Stage46 contract output READY
- Stage47 forward audit output READY
- Stage49 state schema output READY
- Stage52 health gate selection output READY
- `goldsharp_m5.csv`

## Non-negotiable safety boundaries

- GOLD V3 remains audit-only.
- No MT5 orders.
- No MT5 execution BAT.
- No Discord live notification.
- No AI API call.
- No live hook.
- No final signal.
- No candidate pool mutation.
- No high-vol profile demotion/removal.
- No GOLD V2 / old GOLD / DISC8.
- No Stage41 feature-only trading source.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\53_pending_to_closed_shadow_trade_adjudication_audit_only`

Files:

- `gold_v3_53_pending_shadow_trade_ledger.csv`
- `gold_v3_53_closed_shadow_trade_ledger.csv`
- `gold_v3_53_adjudication_parity.csv`
- `gold_v3_53_candidate_outcome_summary.csv`
- `gold_v3_53_validation_matrix.csv`
- `gold_v3_53_shadow_adjudication_summary.json`
- `gold_v3_53_PASTE_ME_SHADOW_ADJUDICATION_SUMMARY.txt`
- `GOLD_V3_53_REPORT.md`

## Validation

Stage53 validates:

1. Stage46/47/49/52 upstream READY.
2. Stage52 selected trade ledger exists and is non-empty.
3. M5 candle file exists and has OHLC rows.
4. Pending shadow trade count equals Stage52 selected trade count.
5. Closed shadow trade count equals pending shadow trade count.
6. Recomputed exit time/reason/result matches Stage52 selected trade ledger.
7. Same-bar adjudication priority is SL.
8. No contract mutation or manual candidate demotion/removal.
9. Safety flags remain OFF.

## Interpretation

READY means the selected Stage52 trades can be converted to pending shadow trades and closed outcomes with full parity to Stage52.
It does not approve live trading.

## Next stage

Stage54 should build restart/replay checkpoint state using Stage49/52/53 ledgers, still audit-only and with no live execution.
