# GOLD V2 17D VOL_TRMEAN32_REFINED reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17D_VOL_TRMEAN32_REFINED_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

17D verifies whether `VOL_TRMEAN32_REFINED` can be placed on the same audited source-row reconciliation chain used by 17C `RANGE96_REFINED` and earlier MEDIUM TIER2_HVT work.

The goal is source-row reconciliation and a candidate source-row freeze preview. It is not live evaluator enablement and not final signal enablement.

## Source of truth

Use only these audited artifacts:

1. `FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_rule_ledgers.csv`
2. `FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_combined_ledgers.csv`
3. `FX_OUTPUTS/gold_v2_17a_medium_full_set_source_arbitration_audit_only/gold_v2_17a_medium_arbitration_matrix.csv`
4. `FX_OUTPUTS/gold_v2_17b_medium_non_tier2_component_replay_planning_audit_only/gold_v2_17b_replay_planning_matrix.csv`

Do not use OHLC to rediscover VOL_TRMEAN32 rows. Do not infer or approximate a VOL_TRMEAN32 live rule from memory or from summary text.

## Expected counts

For `VOL_TRMEAN32_REFINED`, the 17A/17B matrix is the source of truth:

- `rule_ledger_rows = 36`
- `combined_ledger_rows = 104`
- 17A must show `arbitration_status = NEEDS_REPLAY_PARITY`
- 17B must show `planned_step = 17D` and `planning_status = PLAN_READY`

The 13D final rows count of 23 is not used as the 17D input source-row expectation. It belongs to final/internal-priority or reconciled SOT context and must not replace the 17A/17B matrix expectation.

## Input and output contract

### Input CSVs

- `coreb_refined_rule_ledgers.csv`
- `coreb_refined_combined_ledgers.csv`
- `gold_v2_17a_medium_arbitration_matrix.csv`
- `gold_v2_17b_replay_planning_matrix.csv`

### Standardized output fields

17D writes source row files with standardized audit fields when available:

- `strategy_id`
- `entry_time_std`
- `direction_std`
- `dataset_final_std`
- `profit_r_std`
- `outcome`
- `source_key`
- `source_row_hash`

The standardized values are audit fields only. They are not live signal rules.

### Output folder

`FX_OUTPUTS/gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only`

### Main output files

- `GOLD_V2_17D_VOL_TRMEAN32_REFINED_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_17d_vol_trmean32_reconciliation_summary.json`
- `gold_v2_17d_input_audit.csv`
- `gold_v2_17d_vol_trmean32_source_extraction_checks.csv`
- `gold_v2_17d_17a_17b_consistency_checks.csv`
- `gold_v2_17d_vol_trmean32_key_reconciliation_summary.csv`
- `gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json`
- `gold_v2_17d_vol_trmean32_candidate_source_freeze_index.csv`

## Audit method

1. Confirm all required files exist.
2. Extract rows where the detected component column equals `VOL_TRMEAN32_REFINED`.
3. Stop if extracted counts differ from 36 and 104.
4. Stop if 17A/17B counts or statuses differ from the expected plan.
5. Build standardized source keys from dataset, entry time, and direction when columns exist.
6. Stop if any 36 rule-ledger source key is missing from the combined ledger.
7. Write a source-row identity freeze preview only if the above checks pass.

## AI API usage

AI API is not called.

## Safety invariants

The script must keep all of the following false:

- `medium_live_evaluator_allowed`
- `final_signal_allowed`
- `discord_send_allowed`
- `mt5_order_allowed`
- `ai_api_allowed`
- `live_hook_allowed`

NO_SIGNAL is not sent to Discord.

## Stop conditions

Stop with non-zero exit if:

- Any source file is missing.
- The VOL_TRMEAN32 counts do not match 17A/17B and the expected 36/104.
- Required component extraction fails.
- Rule-ledger source keys cannot be reconciled against combined-ledger source keys.
- Any safety flag would become true.
- Only approximate conditions can be produced.

## What 17D implements

17D implements source-row reconciliation and a candidate source-row freeze preview for `VOL_TRMEAN32_REFINED`.

It does not implement an executable live evaluator, final signal, Discord notification, MT5 order, AI review, or live hook.

## Run order

1. Run 17A if its output is missing.
2. Run 17B if its output is missing.
3. Run `scripts/gold_v2_runtime/audit_gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only.py`.

If the BAT is available, run:

`17D_AUDIT_VOL_TRMEAN32_REFINED_RECONCILIATION_AUDIT_ONLY.bat`

## Success condition

17D succeeds only when:

- input audit passes,
- source extraction counts are 36 and 104,
- 17A/17B matrices agree,
- source-key reconciliation has no missing rule keys,
- candidate source-row freeze preview is written,
- every safety flag remains false.

## Do not run / do not enable

Do not enable final signal, Discord, MT5, AI API, live hook, or NO_SIGNAL notification from this step.
