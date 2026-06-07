# GOLD V2 25C41 CoreB G1 right_only row-level export plan audit spec

Date: 2026-06-08
Step: `25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY`
Mode: audit-only export contract plan

## Purpose

25C41 reads the completed 25C40 input-availability audit and defines the exact export contract needed to produce row-level `right_only` comparison evidence for CoreB G1 recovery review.

25C41 is a plan-only step. It must not export rows, re-run a dry-run, recompute CoreB, mutate source, or change conditions.

## 25C40 source-of-truth context

25C40 concluded:

```text
aggregate_right_only_evidence_available=true
row_level_right_only_evidence_available=false
right_only_driver_review_ready=false
row_level_export_plan_required=true
next_recommended_step=25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY
```

The safe conclusion is that driver review cannot start until a row-level export contract is defined and then separately accepted for execution.

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
No new dry-run.
No row-level export execution.
No recompute execution.
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

All control inputs are read from:

```text
FX_OUTPUTS/gold_v2_25c40_coreb_g1_right_only_recovery_input_availability_audit_only/
```

Required files:

```text
02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json
04_25c40_right_only_evidence_availability_matrix.csv
05_25c40_row_level_recovery_readiness_matrix.csv
06_25c40_missing_artifact_export_requirement_matrix.csv
08_25c40_acceptance_gate_matrix.csv
09_25c40_next_step_plan.csv
```

25C41 may reference future execution inputs, but it must not read or recompute those raw execution inputs now.

## Future export source inputs to be defined, not executed

The future export execution step should use the same audited source-of-truth chain as 25C37, not memory or approximate reimplementation:

```text
FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/02_25c36_coreb_g1_over_narrowing_adjustment_plan_summary.json
FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/04_25c36_adjusted_bundle_candidate_matrix.csv
FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/05_25c36_adjusted_bundle_membership.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
FX_OUTPUTS/gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only/02_25c15_coreb_selected_policy_replay_contract_summary.json
FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

The future exporter must reproduce the 25C37 compare construction and write full row-level comparison rows, especially `_merge == right_only`.

## Future export output contract

Future output directory, if later accepted:

```text
FX_OUTPUTS/gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only/
```

Required future output files:

```text
01_25c42_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY_REPORT.md
02_25c42_coreb_g1_right_only_row_level_export_summary.json
03_25c42_input_audit.csv
04_25c42_variant_full_row_level_compare_rows.csv
05_25c42_variant_right_only_row_level_compare_rows.csv
06_25c42_right_only_by_variant_dataset_policy.csv
07_25c42_right_only_export_reconciliation_matrix.csv
08_25c42_execution_boundary_matrix.csv
09_25c42_acceptance_gate_matrix.csv
10_25c42_next_step_plan.csv
```

## Required row-level columns

The future full row-level compare output must contain at least:

```text
variant
dataset
entry_time
policy
_merge
replay_present
target_present
baseline_merge
baseline_replay_present
baseline_target_present
adjusted_replay_present
adjusted_target_present
right_only_reason
source_step
source_artifact
```

The future right_only-only output must contain only rows where:

```text
_merge == right_only
```

## Expected variants

```text
A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8
A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U
A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR
A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR
```

`BASELINE_CURRENT` may be included in the full compare output for reconciliation, but `BASELINE_CURRENT` is not an adjusted variant approval.

## Expected reconciliation checks for future export

Future 25C42 export must stop if the row-level export does not reconcile to 25C37/25C38 aggregate counts:

```text
A001 right_only == 178
A002 right_only == 147
A003 right_only == 200
A004 right_only == 147
A001 both == 68
A002 both == 99
A003 both == 46
A004 both == 99
A001 left_only == 369
A002 left_only == 545
A003 left_only == 225
A004 left_only == 545
```

These values must come from 25C37/25C38 artifacts, not from hard-coded strategy assumptions.

## Trade/evaluation field contract

25C41 is not a trade-level strategy review and does not evaluate TP/SL or outcome.

```text
strategy_id: N/A in this step; no strategy ledger is produced.
entry_time: specified as a required row key for future export only.
direction: N/A.
TP/SL: N/A.
outcome: N/A.
AI API: not called.
```

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/
```

Expected output files:

```text
00_不要_25c41_file_request_list.csv
01_25c41_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY_REPORT.md
02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json
03_25c41_input_audit.csv
04_25c41_future_export_input_contract.csv
05_25c41_future_export_output_schema_contract.csv
06_25c41_future_export_reconciliation_contract.csv
07_25c41_execution_boundary_matrix.csv
08_25c41_acceptance_gate_matrix.csv
09_25c41_next_step_plan.csv
```

## Expected status

```text
COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_READY_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_EXPORT
```

## Success condition

Success requires:

```text
All required 25C40 input artifacts exist.
25C40 summary step/status/audit-only contract is safe.
25C40 dry_run_executed is false.
25C40 source recovery/source mutation/live unblock flags remain false.
25C40 AI/API/live/external flags remain false.
25C40 row_level_export_plan_required is true.
25C41 writes all expected output files.
25C41 records export_executed=false, dry_run_executed=false, and ai_api_called=false.
```

## Stop conditions

Stop if:

```text
Any required 25C40 control input artifact is missing.
25C40 summary is not the expected step or status.
25C40 audit_only is not true.
25C40 input_availability_audit_only is not true.
25C40 dry_run_executed is not false.
25C40 condition_changed is not false.
25C40 source_recovery_executed is not false.
25C40 source_mutation_executed is not false.
25C40 coreb_live_evaluator_unblocked is not false.
25C40 AI API / Discord / MT5 / live hook / final signal flags are unsafe.
25C40 row_level_export_plan_required is not true.
25C40 next plan does not allow 25C41.
```

## BAT execution order

Run only after 25C40 outputs exist locally:

```text
scripts/gold_v2_runtime/bat/25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY.bat
```

## Next-step policy

The next step after successful 25C41 is not automatic execution. It should be an explicit human acceptance gate:

```text
HUMAN_ACCEPT_25C41_BEFORE_25C42_RIGHT_ONLY_ROW_LEVEL_EXPORT
```

Only after explicit acceptance should a 25C42 audit-only row-level export script be created or executed.
