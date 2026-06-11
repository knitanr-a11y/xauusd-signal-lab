# GOLD V3 Stage107 input contract mini handoff

Stage107: `GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY`

Use this together with:

`docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_99_106_DONE_107_NEXT_DIRECTION_AND_TIME_AUDIT_20260611.md`

## Correct source-of-truth

For Stage107, rebuild candidates from GOLD V3 code, not from Stage99-106 CSV outputs.

Read only these GOLD V3 runtime scripts for candidate logic:

- `scripts/gold_v3_runtime/gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py`
- `scripts/gold_v3_runtime/gold_v3_69_live_csv_condition_detector_audit.py`

Stage45 provides candidate definitions and current LONG-style evaluation.
Stage69 imports Stage45 and rebuilds live closed-bar condition candidates.

## Required live candle CSV names

Read exact candle files only:

- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h4.csv`

They are under the user's MT5 Files directory. Do not broadly scan that directory.

## Required GOLD V3 audit artifacts

Read exact GOLD V3 artifacts only if needed:

- `FX_OUTPUTS/gold_v3/50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only/gold_v3_50_rolling_prior_60d_q70_state.csv`
- `FX_OUTPUTS/gold_v3/68_rank_dedup_selection_repro_audit_only/gold_v3_68_rank_dedup_selection_repro_summary.json`
- `FX_OUTPUTS/gold_v3/51_full_candidate_virtual_opportunity_ledger_builder_audit_only/gold_v3_51_virtual_opportunity_ledger.csv`

Stage99-106 outputs are recap/evidence, not Stage107 candidate source-of-truth.

## Candidate construction

Use Stage45 functions:

- `prepare(cdir, "closed", 60, 0.70)`
- `base_candidates()`
- `add_hv_siblings(base_candidates)`
- `source_rows(m15)`
- `opportunities(m15, candidates)`

Then align q70 exactly like Stage69:

- merge Stage50 `m15_time_jst` to `m15.time`
- set `m15_atr28_q = atr28_q70`
- set `is_high_vol = high_vol_pass`

## Entry and profile fields

Use Stage45 opportunity columns:

- `entry_dt`
- `entry_price`
- `tp_usd`
- `sl_usd`
- `horizon_m15`
- `profile_id`

Do not reinterpret `TP180` as 18.0. Current code uses `tp_usd=180.0`.

`H128` means 128 M15 bars. Stage69 candidate key derives `horizon_m5_bars = horizon_m15 * 3`.

## Direction audit

Current evaluation is LONG-style:

- TP = entry + tp
- SL = entry - sl

Stage107 must compare this with SHORT proxy:

- TP = entry - tp
- SL = entry + sl

If TP and SL hit in the same M5 bar, SL wins.

Scan for any side/direction-like column. If absent, report critical directionless LONG-style evaluation finding.

## Outputs

Create only:

- `docs/gold_v3/GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_SPEC_20260611.md`
- `scripts/gold_v3_runtime/gold_v3_107_normal_and_hv_direction_assumption_audit.py`
- `scripts/gold_v3_runtime/bat/run_gold_v3_107_normal_and_hv_direction_assumption.bat`
- `FX_OUTPUTS/gold_v3/107c/paste_me.txt`

User should paste back only `FX_OUTPUTS/gold_v3/107c/paste_me.txt`.

READY: `GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY`
BLOCKED: `GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY`
