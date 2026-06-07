# GOLD V2 25C39 CoreB G1 remaining mismatch route plan audit spec

Date: 2026-06-08
Step: `25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY`
Mode: audit-only route plan

## Purpose

25C39 reads the completed 25C38 result-review outputs and decides which non-execution route should be planned next for the remaining CoreB G1 mismatch.

25C39 must not re-run 25C37, must not change conditions, and must not perform source recovery. It is a planning step only.

## 25C38 source-of-truth context

25C38 concluded:

```text
A003 is best by 25C37 scoring only.
A003 is not approved.
A003 is not live-ready.
A003 is not a source-of-truth replacement.
A003 remains too destructive because right_only increases and both decreases.
No adjusted variant reached exact match.
CoreB live evaluator remains blocked.
```

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

## Source-of-truth inputs

All inputs are read from:

```text
FX_OUTPUTS/gold_v2_25c38_coreb_g1_adjusted_narrowing_result_review_audit_only/
```

Required input files:

```text
02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json
04_25c38_adjusted_variant_tradeoff_matrix.csv
05_25c38_best_variant_review_matrix.csv
06_25c38_remaining_mismatch_decision_matrix.csv
07_25c38_next_step_plan.csv
```

25C39 does not read raw OHLC, does not reconstruct CoreB behavior, and does not approximate source-of-truth logic.

## Trade/evaluation field contract

25C39 is not a trade-level strategy review and does not evaluate TP/SL or outcome.

```text
strategy_id: N/A in this step; no strategy ledger is produced.
entry_time: N/A for raw rows in this step; the route plan uses 25C38 aggregate outputs only.
direction: N/A.
TP/SL: N/A.
outcome: N/A.
AI API: not called.
```

The review uses aggregate mismatch and route fields:

```text
variant
both
left_only
right_only
left_only_reduction
right_only_increase
both_loss
review_class
route_id
route
recommended
allowed_now
```

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c39_coreb_g1_remaining_mismatch_route_plan_audit_only/
```

Expected output files:

```text
00_不要_25c39_file_request_list.csv
01_25c39_GOLD_V2_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY_REPORT.md
02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json
03_25c39_input_audit.csv
04_25c39_route_option_matrix.csv
05_25c39_route_recommendation_matrix.csv
06_25c39_execution_boundary_matrix.csv
07_25c39_acceptance_gate_matrix.csv
08_25c39_next_step_plan.csv
```

## Route options to evaluate

25C39 evaluates these non-execution routes:

```text
R001_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST
R002_HYBRID_VARIANT_PLAN_AFTER_RIGHT_ONLY_DRIVER_REVIEW
R003_LESS_DESTRUCTIVE_THRESHOLD_PLAN_ONLY
R004_STOP_ADJUSTED_NARROWING_AS_INSUFFICIENT
R005_SOURCE_RECOVERY_OR_SOURCE_MUTATION_BLOCKED
R006_COREB_LIVE_EVALUATOR_OR_EXTERNAL_ACTIONS_BLOCKED
```

Expected recommendation:

```text
RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST
```

Reason:

```text
All adjusted variants still increase right_only and lose both. Before designing another exclusion bundle, audit whether existing artifacts contain enough row-level right_only evidence to identify which filters damaged target-matching rows.
```

## Success condition

Successful 25C39 status:

```text
COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_READY_AUDIT_ONLY_NEXT_AUDIT_REQUIRED
```

Success requires:

```text
All required 25C38 input artifacts exist.
25C38 summary step/status/audit-only contract is safe.
25C38 dry_run_executed is false.
25C38 source recovery/source mutation/live unblock flags remain false.
25C38 AI/API/live/external flags remain false.
25C39 writes all expected output files.
25C39 records dry_run_executed=false and ai_api_called=false.
```

## Stop conditions

Stop if:

```text
Any required 25C38 input artifact is missing.
25C38 summary is not the expected step or status.
25C38 audit_only is not true.
25C38 result_review_only is not true.
25C38 dry_run_executed is not false.
25C38 condition_changed is not false.
25C38 source_recovery_executed is not false.
25C38 source_mutation_executed is not false.
25C38 coreb_live_evaluator_unblocked is not false.
25C38 AI API / Discord / MT5 / live hook / final signal flags are unsafe.
25C38 next plan does not allow 25C39 route planning.
```

## Files to inspect after running

```text
03_25c39_input_audit.csv
04_25c39_route_option_matrix.csv
05_25c39_route_recommendation_matrix.csv
06_25c39_execution_boundary_matrix.csv
07_25c39_acceptance_gate_matrix.csv
08_25c39_next_step_plan.csv
02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json
01_25c39_GOLD_V2_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY_REPORT.md
```

## BAT execution order

Run only after 25C38 outputs exist locally:

```text
scripts/gold_v2_runtime/bat/25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY.bat
```

Do not run any 25C37 or 25C38 dry-run/review again for this step unless explicitly needed for audit reproduction.

## Next-step policy

Expected next recommended step:

```text
25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY
```

25C40 should only check whether existing artifacts contain enough right_only row-level evidence for recovery review. It must not execute a new dry-run or condition change.

Any future dry-run requires a separate explicit human acceptance gate.
