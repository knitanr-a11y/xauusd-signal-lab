# GOLD V2 25C38 CoreB G1 adjusted narrowing result review audit spec

Date: 2026-06-08
Step: `25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY`
Mode: audit-only result review

## Purpose

Review the already completed 25C37 adjusted narrowing dry-run outputs.

25C38 is not a dry-run step. It reads audited 25C37 artifacts and produces review-only matrices that explain why A003 is only the current scoring best variant and is not approved, not live-ready, and not a source-of-truth replacement.

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
No new dry-run.
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

If the 25C37 contract is missing or unsafe, 25C38 must stop with `25C38_STOP_*` and must not continue to review conclusions.

## Source-of-truth inputs

All inputs are read from:

```text
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/
```

Required input files:

```text
02_25c37_coreb_g1_adjusted_narrowing_dry_run_summary.json
04_25c37_variant_filter_contract.csv
05_25c37_variant_compare_matrix.csv
06_25c37_variant_delta_matrix.csv
07_25c37_variant_by_dataset_policy.csv
09_25c37_acceptance_gate_matrix.csv
```

The script does not read raw OHLC, does not reconstruct CoreB behavior, and does not approximate source-of-truth logic.

## Input schema notes

`05_25c37_variant_compare_matrix.csv` must contain at least:

```text
variant
replay_g1_rows
both
left_only
right_only
exact_match
```

Expected variants:

```text
BASELINE_CURRENT
A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8
A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U
A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR
A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR
```

Expected 25C37 source counts from the handoff:

| variant | replay_g1_rows | both | left_only | right_only | exact_match |
|---|---:|---:|---:|---:|---|
| BASELINE_CURRENT | 981 | 168 | 813 | 78 | False |
| A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8 | 437 | 68 | 369 | 178 | False |
| A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U | 644 | 99 | 545 | 147 | False |
| A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR | 271 | 46 | 225 | 200 | False |
| A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR | 644 | 99 | 545 | 147 | False |

## Trade/evaluation field contract

25C38 is not a trade-level strategy review and does not evaluate TP/SL or outcome.

```text
strategy_id: N/A in this step; no strategy ledger is produced.
entry_time: N/A for raw rows in this step; the review uses 25C37 aggregate compare artifacts only.
direction: N/A.
TP/SL: N/A.
outcome: N/A.
AI API: not called.
```

CoreB G1 identity is reviewed by aggregate mismatch fields:

```text
variant
dataset
policy
_merge
replay_g1_rows
both
left_only
right_only
```

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c38_coreb_g1_adjusted_narrowing_result_review_audit_only/
```

Expected output files:

```text
00_不要_25c38_file_request_list.csv
01_25c38_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json
03_25c38_input_audit.csv
04_25c38_adjusted_variant_tradeoff_matrix.csv
05_25c38_best_variant_review_matrix.csv
06_25c38_remaining_mismatch_decision_matrix.csv
07_25c38_next_step_plan.csv
```

## Review metrics

25C38 computes, for each adjusted variant:

```text
left_only_reduction = baseline_left_only - variant_left_only
right_only_increase = variant_right_only - baseline_right_only
both_loss = baseline_both - variant_both
replay_row_reduction = baseline_replay_g1_rows - variant_replay_g1_rows
over_narrowing_score = right_only_increase + both_loss
net_tradeoff_score = left_only_reduction - over_narrowing_score
```

The review must explicitly mark:

```text
usable_as_is = False
live_ready = False
approval_status = NOT_APPROVED_REVIEW_ONLY
source_of_truth_replacement = False
```

## Expected review interpretation

A003 is expected to rank best by 25C37 scoring, but this does not mean adoption.

Expected conclusions:

```text
A003: best by scoring only; too destructive because right_only increases and both decreases.
A001: less destructive than A003 but still not exact.
A002/A004: equivalent in 25C37; less destructive than A003 but only moderate left_only improvement.
No variant is CoreB-live ready.
No variant is approved.
No variant is a source-of-truth replacement.
```

## Success condition

Successful 25C38 status:

```text
COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED
```

Success requires:

```text
All required 25C37 input artifacts exist.
25C37 summary step/status/audit-only contract is safe.
25C37 source recovery/source mutation/live unblock flags remain false.
Expected baseline and A001-A004 variants exist.
25C38 writes all expected output files.
25C38 records dry_run_executed=false and ai_api_called=false.
```

## Stop conditions

Stop if:

```text
Any required 25C37 input artifact is missing.
25C37 summary is not the expected step or review-required status.
25C37 audit_only is not true.
25C37 dry_run_executed is not true.
25C37 condition_changed is not false.
25C37 source_recovery_executed is not false.
25C37 source_mutation_executed is not false.
25C37 coreb_live_evaluator_unblocked is not false.
Expected baseline/A001/A002/A003/A004 variants are missing.
```

## Files to inspect after running

```text
03_25c38_input_audit.csv
04_25c38_adjusted_variant_tradeoff_matrix.csv
05_25c38_best_variant_review_matrix.csv
06_25c38_remaining_mismatch_decision_matrix.csv
07_25c38_next_step_plan.csv
02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json
01_25c38_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
```

## BAT execution order

Run only after 25C37 outputs exist locally:

```text
scripts/gold_v2_runtime/bat/25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY.bat
```

Do not run any 25C37 dry-run again for this step.

## Next-step policy

25C38 may recommend a next planning step such as:

```text
25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY
```

That next planning step may discuss whether to pursue less destructive thresholds, right_only recovery review, hybrid variant planning, or stopping adjusted narrowing. It must not execute a new dry-run without a separate explicit acceptance gate.
