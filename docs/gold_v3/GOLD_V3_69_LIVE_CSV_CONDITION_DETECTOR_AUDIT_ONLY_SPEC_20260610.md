# GOLD V3 Stage69 — Live CSV Condition Detector Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage69 verifies that GOLD V3 candidate signal conditions can be detected from the live CSV closed candle set.

It reuses the audited Stage45 candidate condition functions and the audited Stage50 high-volatility q70 state so that the detector can rebuild candidate condition rows directly from:

- `goldsharp_m15.csv`
- `goldsharp_h4.csv`
- `goldsharp_m5.csv` only for input presence/parity continuity; no future outcome adjudication is performed

Stage69 does **not** adjudicate TP/SL, does **not** call MT5, does **not** notify Discord, does **not** call AI APIs, and does **not** enable live final signal.

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

Stage69 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

Stage69 must use the latest row in `goldsharp_m15.csv` as the latest closed M15 row.

## 4. Required inputs

Default Files directory:

`Files`

Required CSV inputs:

- `goldsharp_m15.csv`
- `goldsharp_h4.csv`
- `goldsharp_m5.csv`

Required GOLD V3 audit artifacts:

- `FX_OUTPUTS/gold_v3/68_rank_dedup_selection_repro_audit_only/gold_v3_68_rank_dedup_selection_repro_summary.json`
- `FX_OUTPUTS/gold_v3/51_full_candidate_virtual_opportunity_ledger_builder_audit_only/gold_v3_51_virtual_opportunity_ledger.csv`
- `FX_OUTPUTS/gold_v3/50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only/gold_v3_50_rolling_prior_60d_q70_state.csv`
- Stage45 runner: `scripts/gold_v3_runtime/gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py`

Stage68 must be READY:

`GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_READY_AUDIT_ONLY`

## 5. Detection source

Stage69 must call Stage45 functions:

- `prepare(candle_dir, "closed", 60, 0.70)`
- `base_candidates()`
- `add_hv_siblings(base_candidates)`
- `opportunities(m15, all_candidates)`

Stage69 must **not** call Stage45 `evaluate()` for signal detection because `evaluate()` uses future M5 rows to adjudicate TP/SL/timeout.

## 6. Q70 high-volatility state

To match Stage51, Stage69 must override the Stage45 internally calculated q70 fields with Stage50 audited q70 state:

- merge Stage50 q70 by M15 `time` / `m15_time_jst`
- set `m15_atr28_q = atr28_q70`
- set `is_high_vol = high_vol_pass`

## 7. Candidate key contract

Use this exact ordered column list:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

Do not omit profile fields.

Do not merge high-vol sibling profiles.

Do not use candidate label alone.

## 8. Stage51 parity contract

Stage69 detects raw candidate condition rows. Stage51 contains only evaluated complete opportunities.

READY requires:

- all Stage51 rows are detected by Stage69 using `entry_dt + candidate_key`
- candidate key reconstruction succeeds
- no OHLC re-adjudication is performed
- live CSV latest closed M15 row is evaluated for candidate conditions

Stage69 may produce additional detected rows not present in Stage51 because they are live/forward raw condition rows without future M5 outcome adjudication. These are diagnostic and not blockers.

## 9. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/69_live_csv_condition_detector_audit_only`

Required outputs:

- `gold_v3_69_detected_candidate_conditions.csv`
- `gold_v3_69_latest_closed_condition_candidates.csv`
- `gold_v3_69_stage51_detection_parity.csv`
- `gold_v3_69_detector_extra_conditions.csv`
- `gold_v3_69_candidate_condition_summary.csv`
- `gold_v3_69_blocker_matrix.csv`
- `gold_v3_69_validation_matrix.csv`
- `gold_v3_69_live_csv_condition_detector_summary.json`
- `gold_v3_69_PASTE_ME_LIVE_CSV_CONDITION_DETECTOR_SUMMARY.txt`
- `GOLD_V3_69_REPORT.md`

## 10. READY conditions

Stage69 is READY only if:

- Stage68 is READY.
- Required live CSV files exist.
- Stage45 runner exists and can be imported.
- Stage50 q70 state exists and is merged.
- Stage51 ledger exists.
- Stage69 detects every Stage51 `entry_dt + candidate_key` row.
- latest closed M15 row is evaluated by the detector.
- all live/MT5/Discord/AI/final-signal flags remain false.
- `csv_open_bar_exclusion_required=false` is preserved.

## 11. BLOCKED conditions

Stage69 must BLOCK if:

- Stage68 is missing or not READY.
- required CSVs are missing.
- Stage45 import fails.
- Stage50 q70 cannot be merged.
- Stage51 ledger is missing.
- any Stage51 row is not detected from CSV conditions.
- candidate key cannot be reconstructed from the exact ordered columns.
- any live/MT5/Discord/AI/final-signal flag is true.

## 12. Runner

Script:

`scripts/gold_v3_runtime/gold_v3_69_live_csv_condition_detector_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_69_live_csv_condition_detector_audit.bat`

The BAT is a no-argument local audit runner only.
