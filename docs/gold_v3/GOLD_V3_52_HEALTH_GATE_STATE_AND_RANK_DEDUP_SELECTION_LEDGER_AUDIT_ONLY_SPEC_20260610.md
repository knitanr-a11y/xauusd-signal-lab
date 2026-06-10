# GOLD V3 52 health gate state and rank-dedup selection ledger audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_52_HEALTH_GATE_STATE_AND_RANK_DEDUP_SELECTION_LEDGER_SPEC_READY_AUDIT_ONLY`

## Purpose

Build persistent audit-only ledgers for:

1. `health_gate_state`
2. `rank_dedup_selection_ledger`

Stage52 reads the Stage51 full-candidate virtual opportunity ledger and reproduces the Stage45 strict rolling health gate selection behavior.

Stage52 does **not** implement live trading, does **not** send signals, and does **not** change candidate or gate logic.

## Frozen upstream contract

Stage52 must preserve:

- `htf_asof = closed`
- OPEN asof prohibited
- full Stage45 base + HV sibling candidate pool retained
- high-vol profiles retained:
  - `HV_TP180_SL70_H128`
  - `HV_TP200_SL80_H128`
  - `HV_TP220_SL90_H128`
- no manual candidate demotion/removal
- strict rolling health gate unchanged
- all candidates virtually monitored

## Strict rolling health gate contract

Use the Stage45 gate rules exactly:

- sort opportunities by `entry_dt`, `priority`, `candidate_label`
- group by `entry_dt`
- for each candidate opportunity at that timestamp:
  - read prior virtual result history for that candidate only
  - if history count `< min_history`, candidate is eligible
  - otherwise eligible only when:
    - rolling PF `>= 1.10`
    - loss streak `< 3`
- select the first eligible candidate after `priority`, `candidate_label` ordering
- after the timestamp is processed, append **all** candidate results at that timestamp into their candidate histories, including unselected candidates

Frozen parameters:

- window: `30`
- min_history: `20`
- pf_threshold: `1.10`
- loss_streak_lt: `3`
- virtual_monitoring: `true`

## Required upstream artifacts

- Stage46 contract output READY
- Stage47 forward audit output READY
- Stage49 state schema output READY
- Stage51 virtual opportunity ledger READY
- Stage47 replay strict gate trade ledger:
  - `stage47_replay/gold_v3_45_hv_sibling_strict_gate_trade_ledger.csv`

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

`Files\\FX_OUTPUTS\\gold_v3\\52_health_gate_state_rank_dedup_audit_only`

Files:

- `gold_v3_52_health_gate_state.csv`
- `gold_v3_52_rank_dedup_selection_ledger.csv`
- `gold_v3_52_selected_trade_ledger.csv`
- `gold_v3_52_selection_parity.csv`
- `gold_v3_52_candidate_selection_summary.csv`
- `gold_v3_52_validation_matrix.csv`
- `gold_v3_52_health_gate_selection_summary.json`
- `gold_v3_52_PASTE_ME_HEALTH_GATE_SELECTION_SUMMARY.txt`
- `GOLD_V3_52_REPORT.md`

## Validation

Stage52 validates:

1. Stage46/47/49/51 upstream READY.
2. Stage51 virtual ledger is present and non-empty.
3. Strict gate parameters are frozen as `30/20/PF>=1.10/loss_streak<3`.
4. Selected trade count equals Stage47 strict gate trade ledger.
5. Selected entry timestamps match Stage47.
6. Selected candidate labels match Stage47.
7. Candidate-level selected counts match Stage47.
8. No contract mutation or manual candidate demotion/removal.
9. Safety flags remain OFF.

## Interpretation

READY means the audit-only health gate state and rank-dedup selection ledger reproduce the Stage47 strict gate trade ledger.
It does not approve live trading.

## Next stage

Stage53 should build the pending-to-closed shadow trade adjudication ledger using the Stage52 selected ledger, still audit-only and with no MT5 execution.
