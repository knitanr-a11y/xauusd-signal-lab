# GOLD V2 25C40 CoreB G1 right_only recovery input availability audit spec

Date: 2026-06-08
Step: `25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY`
Mode: audit-only input availability audit

## Purpose

25C40 reads the completed 25C39 route-plan outputs and audits whether existing 25C37/25C38/25C39 artifacts contain enough row-level `right_only` evidence to begin a right_only recovery driver review.

25C40 is not a dry-run step. It does not regenerate CoreB G1 comparisons. It only checks what already exists in `FX_OUTPUTS`.

## 25C39 source-of-truth context

25C39 selected:

```text
RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST
```

Reason:

```text
All adjusted variants increased right_only and lost both rows. Before designing another exclusion bundle, audit whether existing artifacts contain enough row-level right_only evidence to identify which target-matching rows were damaged.
```

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
No new dry-run.
No right_only export execution.
No live evaluator unblock.
No final signal.
No Discord notification.
No MT5 order.
No AI API call.
No live hook.
NO_SIGNAL must not notify Discord.
REQUEST_MORE_AUDIT is not source recovery approval.
Old GOLD / DISC8 remains quarantined.
```

## Required source-of-truth inputs

All required control inputs are read from:

```text
FX_OUTPUTS/gold_v2_25c39_coreb_g1_remaining_mismatch_route_plan_audit_only/
```

Required files:

```text
02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json
05_25c39_route_recommendation_matrix.csv
06_25c39_execution_boundary_matrix.csv
07_25c39_acceptance_gate_matrix.csv
08_25c39_next_step_plan.csv
```

## Evidence candidate inputs

25C40 audits availability of right_only evidence in existing artifacts under:

```text
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/
FX_OUTPUTS/gold_v2_25c38_coreb_g1_adjusted_narrowing_result_review_audit_only/
FX_OUTPUTS/gold_v2_25c39_coreb_g1_remaining_mismatch_route_plan_audit_only/
```

Expected evidence candidates include:

```text
25C37: 05_25c37_variant_compare_matrix.csv
25C37: 06_25c37_variant_delta_matrix.csv
25C37: 07_25c37_variant_by_dataset_policy.csv
25C37: 08_25c37_best_variant_left_only_samples.csv
25C38: 04_25c38_adjusted_variant_tradeoff_matrix.csv
25C38: 05_25c38_best_variant_review_matrix.csv
25C38: 06_25c38_remaining_mismatch_decision_matrix.csv
25C39: 05_25c39_route_recommendation_matrix.csv
```

25C40 may also scan right_only-named CSV files in those same output directories, but it must not read unrelated old GOLD/DISC8 files or raw OHLC.

## Row-level readiness definition

A right_only driver review is ready only if at least one existing CSV contains row-level right_only evidence with the following fields:

```text
variant
dataset
entry_time
policy
_merge
```

and contains rows where:

```text
_merge == right_only
```

Aggregate counts alone are not enough for driver review.

## Trade/evaluation field contract

25C40 is not a trade-level strategy review and does not evaluate TP/SL or outcome.

```text
strategy_id: N/A in this step; no strategy ledger is produced.
entry_time: checked only as a row-key availability field for right_only evidence; no trade replay is performed.
direction: N/A.
TP/SL: N/A.
outcome: N/A.
AI API: not called.
```

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c40_coreb_g1_right_only_recovery_input_availability_audit_only/
```

Expected output files:

```text
00_不要_25c40_file_request_list.csv
01_25c40_GOLD_V2_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY_REPORT.md
02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json
03_25c40_input_audit.csv
04_25c40_right_only_evidence_availability_matrix.csv
05_25c40_row_level_recovery_readiness_matrix.csv
06_25c40_missing_artifact_export_requirement_matrix.csv
07_25c40_execution_boundary_matrix.csv
08_25c40_acceptance_gate_matrix.csv
09_25c40_next_step_plan.csv
```

## Expected result if standard 25C37/25C38 outputs are unchanged

Expected status:

```text
COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_COMPLETED_AUDIT_ONLY_ROW_LEVEL_EXPORT_PLAN_REQUIRED
```

Expected interpretation:

```text
Aggregate right_only evidence exists.
Row-level right_only evidence is not available in standard 25C37/25C38/25C39 outputs.
Driver review is not ready.
The next step should be an export-contract plan, not export execution and not a dry-run.
```

Expected next step:

```text
25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY
```

## Alternate result if row-level right_only artifact already exists

If an existing CSV already contains `variant/dataset/entry_time/policy/_merge=right_only`, 25C40 may produce:

```text
COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_COMPLETED_AUDIT_ONLY_DRIVER_REVIEW_READY
```

and recommend:

```text
25C41_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY
```

This still does not allow live evaluator, final signal, Discord, MT5, AI API, source recovery, source mutation, or a future dry-run.

## Success condition

Success requires:

```text
All required 25C39 input artifacts exist.
25C39 summary step/status/audit-only contract is safe.
25C39 dry_run_executed is false.
25C39 source recovery/source mutation/live unblock flags remain false.
25C39 AI/API/live/external flags remain false.
25C39 selected route is RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST.
25C40 writes all expected output files.
25C40 records dry_run_executed=false and ai_api_called=false.
```

## Stop conditions

Stop if:

```text
Any required 25C39 control input artifact is missing.
25C39 summary is not the expected step or status.
25C39 audit_only is not true.
25C39 plan_only is not true.
25C39 dry_run_executed is not false.
25C39 condition_changed is not false.
25C39 source_recovery_executed is not false.
25C39 source_mutation_executed is not false.
25C39 coreb_live_evaluator_unblocked is not false.
25C39 AI API / Discord / MT5 / live hook / final signal flags are unsafe.
25C39 selected_route is not RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST.
25C39 next plan does not allow 25C40.
```

Missing row-level right_only evidence is not a hard stop. It is the expected audit finding and should route to 25C41 export-plan audit-only.

## Files to inspect after running

```text
03_25c40_input_audit.csv
04_25c40_right_only_evidence_availability_matrix.csv
05_25c40_row_level_recovery_readiness_matrix.csv
06_25c40_missing_artifact_export_requirement_matrix.csv
07_25c40_execution_boundary_matrix.csv
08_25c40_acceptance_gate_matrix.csv
09_25c40_next_step_plan.csv
02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json
01_25c40_GOLD_V2_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY_REPORT.md
```

## BAT execution order

Run only after 25C39 outputs exist locally:

```text
scripts/gold_v2_runtime/bat/25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY.bat
```

Do not run any 25C37 dry-run or future export/recompute in 25C40.

## Next-step policy

If row-level evidence is missing, the next recommended step is:

```text
25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY
```

25C41 should define the exact export contract only. If any later step needs to recompute or export row-level comparison rows, that execution must have a separate explicit acceptance gate.
