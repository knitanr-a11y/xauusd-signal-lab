# GOLD V2 25B5 CoreB same_count replay dry-run audit spec

Date: 2026-06-07
Step: `25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_AUDIT_ONLY`
Mode: audit-only dry-run replay diagnostics

## Purpose

25B4 froze the replay plan and contract. 25B5 performs a dry-run diagnostic from frozen source files and reports parity gaps.

25B5 is not a live evaluator and does not unblock CoreB.

## Inputs

25B5 reads:

```text
Files/FX_OUTPUTS/gold_v2_25b4_coreb_same_count_replay_plan_audit_only/gold_v2_25b4_coreb_same_count_replay_plan_summary.json
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

From the 25B3 file audit it resolves:

```text
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
frozen_coreB_same_count_source_universe_20260604.json
frozen_coreB_rr125_source_rule_conditions_20260603.json
frozen_coreB_combined_evaluator_definition_20260604.json
```

## Dry-run semantics

25B5 uses frozen rule keys only:

```text
policy,candidate_id,origin_id,direction,variant,rr_bucket
```

It marks raw ledger rows that match selected rules and raw rows that match the same_count source universe. It then creates a diagnostic candidate table using:

```text
entry_logic = selected_rule_hit AND same_count_source_hit_count >= 15
```

This is a dry-run semantics probe. It is not promoted to source truth unless parity is later proven.

## Outputs

```text
GOLD_V2_25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_AUDIT_ONLY_REPORT.md
gold_v2_25b5_input_audit.csv
gold_v2_25b5_rule_key_audit.csv
gold_v2_25b5_raw_match_summary.csv
gold_v2_25b5_dry_run_candidate_rows.csv
gold_v2_25b5_target_compare_same_count_ge15.csv
gold_v2_25b5_parity_summary.csv
gold_v2_25b5_execution_blockers.csv
gold_v2_25b5_coreb_same_count_replay_dry_run_summary.json
```

## Required pass gates for future unblock

A later unblock would require all of these. 25B5 does not grant unblock.

```text
missing replay keys = 0
extra replay keys = 0
same_count exact value match for all target rows
final CoreB 125-row parity if final SOT target is used
cluster_id/membership parity if accepted as source truth
```

## Forbidden

```text
target fitting
static window substitution
raw entry count substitution
connected-component substitution
manual cluster assignment
old quarantined artifacts
external or final signal action
```

## Expected status

```text
COREB_SAME_COUNT_REPLAY_DRY_RUN_COMPLETED_AUDIT_ONLY_PARITY_REVIEW_REQUIRED
```

or a STOP status if inputs are missing or unsafe.
