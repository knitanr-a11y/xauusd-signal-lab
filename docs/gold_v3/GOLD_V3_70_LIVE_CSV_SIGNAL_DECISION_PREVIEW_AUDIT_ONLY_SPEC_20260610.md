# GOLD V3 Stage70 — Live CSV Signal Decision Preview Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage70 produces an audit-only `SIGNAL` / `NO_SIGNAL` preview for the latest closed M15 row detected by Stage69.

It combines:

1. Stage69 latest closed candidate condition detection,
2. Stage67 rehydrated candidate-level rolling health state,
3. deterministic rank/dedup ordering,
4. strict safety flags.

Stage70 is not live trading and does not enable final signals.

## 2. Non-negotiable constraints

- GOLD V3 only.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
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

Stage70 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

Stage70 must treat the Stage69 latest closed M15 timestamp as closed.

## 4. Required inputs

Default GOLD V3 output root:

`Files/FX_OUTPUTS/gold_v3`

Required Stage69 inputs:

- `69_live_csv_condition_detector_audit_only/gold_v3_69_live_csv_condition_detector_summary.json`
- `69_live_csv_condition_detector_audit_only/gold_v3_69_latest_closed_condition_candidates.csv`

Required Stage67 input:

- `67_health_gate_rehydration_audit_only/gold_v3_67_health_gate_rehydrated_candidate_state.csv`

Required Stage68 input:

- `68_rank_dedup_selection_repro_audit_only/gold_v3_68_rank_dedup_selection_repro_summary.json`

Stage69 must be READY:

`GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY`

Stage68 must be READY:

`GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_READY_AUDIT_ONLY`

## 5. Candidate key contract

Use this exact ordered column list:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

Do not omit profile fields.

Do not merge high-vol sibling profiles.

Do not use candidate label alone.

## 6. Signal decision contract

For the Stage69 latest closed M15 timestamp:

1. If no condition candidate exists:
   - output one decision row with `decision=NO_SIGNAL`
   - `no_signal_reason=CONDITION_NOT_MET`
2. If condition candidates exist:
   - merge candidates to Stage67 candidate health state by exact candidate key
   - rows with `health_gate_pass=true` are eligible
   - if no eligible candidate remains, output `decision=NO_SIGNAL` and `no_signal_reason=HEALTH_GATE_BLOCKED`
   - if eligible candidates exist, sort by:
     - `priority` ascending
     - `candidate_label` ascending
     - `candidate_key` ascending
     - `condition_id` ascending
   - output the first row as `decision=SIGNAL`

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/70_live_csv_signal_decision_preview_audit_only`

Required outputs:

- `gold_v3_70_latest_closed_candidate_screen.csv`
- `gold_v3_70_latest_closed_signal_decision.csv`
- `gold_v3_70_blocker_matrix.csv`
- `gold_v3_70_validation_matrix.csv`
- `gold_v3_70_live_csv_signal_decision_preview_summary.json`
- `gold_v3_70_PASTE_ME_LIVE_CSV_SIGNAL_DECISION_PREVIEW_SUMMARY.txt`
- `GOLD_V3_70_REPORT.md`

## 8. READY conditions

Stage70 is READY if:

- Stage69 is READY.
- Stage68 is READY.
- Stage67 candidate health state exists.
- Candidate key reconstruction succeeds.
- If latest candidates exist, every latest candidate has a Stage67 health state row.
- A deterministic `SIGNAL` or `NO_SIGNAL` decision row is produced.
- all live/MT5/Discord/AI/final-signal flags remain false.
- `csv_open_bar_exclusion_required=false` is preserved.

`NO_SIGNAL` is allowed and is READY when produced deterministically.

## 9. BLOCKED conditions

Stage70 must BLOCK if:

- Stage69 is missing or not READY.
- Stage68 is missing or not READY.
- Stage67 candidate health state is missing.
- candidate key cannot be reconstructed.
- latest candidates exist but any candidate lacks Stage67 health state.
- no decision row can be produced.
- any live/MT5/Discord/AI/final-signal flag is true.

## 10. Runner

Script:

`scripts/gold_v3_runtime/gold_v3_70_live_csv_signal_decision_preview_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_70_live_csv_signal_decision_preview_audit.bat`

The BAT is a no-argument local audit runner only.
