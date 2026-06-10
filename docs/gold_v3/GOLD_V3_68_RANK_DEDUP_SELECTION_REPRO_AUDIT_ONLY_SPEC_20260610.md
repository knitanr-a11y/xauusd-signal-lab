# GOLD V3 Stage68 — Rank/Dedup Selection Reproduction Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage68 reproduces rank/dedup selection from the Stage67 rehydrated rolling health gate event state.

It selects at most one candidate per M15 opportunity timestamp by applying:

1. the Stage67 `health_gate_pass` state, then
2. deterministic rank ordering by `priority`, then
3. deterministic tie-break by candidate identity.

This is not live trading, not a live evaluator, not a final signal, not Discord notification, not MT5 execution, and not AI analysis.

## 2. Non-negotiable constraints

- GOLD V3 only.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as trading source.
- Do not create MT5 order BATs.
- Do not send Discord notifications.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Keep every observed candidate in the pool.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

The human clarified:

`open中の足はCSVには入りません`

Stage68 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

No open-bar exclusion filter should be introduced.

## 4. Required inputs

Default GOLD V3 output root:

`Files\\FX_OUTPUTS\\gold_v3`

Required Stage67 inputs:

- `67_health_gate_rehydration_audit_only/gold_v3_67_health_gate_rehydration_summary.json`
- `67_health_gate_rehydration_audit_only/gold_v3_67_health_gate_event_ledger.csv`
- `67_health_gate_rehydration_audit_only/gold_v3_67_health_gate_rehydrated_candidate_state.csv`

Stage67 must be READY:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_READY_AUDIT_ONLY`

Required Stage66 input for rank metadata:

- `66_virtual_monitoring_state_audit_only/gold_v3_66_virtual_opportunity_q70_joined_ledger.csv`

Required parity reference:

- `52_health_gate_state_rank_dedup_audit_only/gold_v3_52_selected_trade_ledger.csv`

The Stage52 reference is used only for audit parity. It is not a fallback for missing Stage67 health state.

## 5. Candidate key contract

Use this exact ordered column list:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

Do not omit profile fields.

Do not merge high-vol sibling profiles.

Do not use a looser candidate label only key.

## 6. Rank/dedup selection contract

For each M15 event timestamp:

1. Retain all candidate rows in the event ledger.
2. Mark rows with Stage67 `health_gate_pass=true` as eligible.
3. Sort eligible rows by:
   - `priority` ascending
   - `candidate_label` ascending
   - `candidate_key` ascending
   - `opportunity_id` ascending
4. Select the first eligible row.
5. If no row is eligible, output a no-signal row with reason `NO_ELIGIBLE_CANDIDATE`.

This stage does not remove candidates from the pool. It only reproduces the selected rank/dedup row for the timestamp.

## 7. Outputs

Output folder:

`Files\\FX_OUTPUTS\\gold_v3\\68_rank_dedup_selection_repro_audit_only`

Required outputs:

- `gold_v3_68_rank_dedup_selection_ledger.csv`
- `gold_v3_68_selected_trade_ledger.csv`
- `gold_v3_68_candidate_selection_summary.csv`
- `gold_v3_68_stage52_selection_parity.csv`
- `gold_v3_68_blocker_matrix.csv`
- `gold_v3_68_validation_matrix.csv`
- `gold_v3_68_rank_dedup_selection_repro_summary.json`
- `gold_v3_68_PASTE_ME_RANK_DEDUP_SELECTION_REPRO_SUMMARY.txt`
- `GOLD_V3_68_REPORT.md`

## 8. READY conditions

Stage68 is READY only if:

- Stage67 summary is READY.
- Stage67 event ledger and candidate state exist.
- Stage66 joined ledger exists and can provide rank metadata.
- Stage67 event ledger rows merge one-to-one with Stage66 joined rows by `opportunity_id` and exact candidate key.
- `priority` is available and numeric for all events.
- Rank/dedup selection is deterministic.
- Stage52 selected trade ledger exists for audit parity.
- Selected `opportunity_id` set exactly matches Stage52 selected trade ledger.
- All safety flags remain false.
- `csv_open_bar_exclusion_required=false` is preserved.

## 9. BLOCKED conditions

Stage68 must BLOCK if any of these occurs:

- Stage67 is missing or not READY.
- Stage67 event ledger is missing or empty.
- Stage66 rank metadata cannot be joined one-to-one.
- Candidate key cannot be reconstructed from the exact ordered columns.
- Rank priority is missing or non-numeric.
- Stage52 parity reference is missing.
- Stage68 selected `opportunity_id` set does not match Stage52 selected trade ledger.
- Any live/MT5/Discord/AI/final-signal flag is true.

## 10. Runner

Script:

`scripts/gold_v3_runtime/gold_v3_68_rank_dedup_selection_repro_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_68_rank_dedup_selection_repro_audit.bat`

The BAT is a no-argument local audit runner only.
