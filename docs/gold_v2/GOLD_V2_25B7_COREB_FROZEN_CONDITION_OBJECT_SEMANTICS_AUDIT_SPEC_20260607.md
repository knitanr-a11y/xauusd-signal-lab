# GOLD V2 25B7 CoreB frozen condition object semantics audit spec

Date: 2026-06-07
Step: `25B7_COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_AUDIT_ONLY`
Mode: audit-only condition-object inspection

## Purpose

25B6 showed that key-only matching cannot reproduce CoreB target parity.

25B7 inspects the full frozen JSON condition objects and identifies what semantics were lost by the 25B5 key-only probe.

25B7 does not execute a new CoreB replay. It only inventories JSON objects, fields, operators, collapsed-key groups, and feasibility for a later non-key-only dry run.

## Inputs

25B7 reads:

```text
Files/FX_OUTPUTS/gold_v2_25b6_coreb_dry_run_parity_review_audit_only/gold_v2_25b6_coreb_dry_run_parity_review_summary.json
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

From 25B3 file audit it resolves:

```text
frozen_coreB_rr125_source_rule_conditions_20260603.json
frozen_coreB_same_count_source_universe_20260604.json
frozen_coreB_combined_evaluator_definition_20260604.json
frozen_coreB_rr125_buy_confluence_rules_20260603.json
```

## Outputs

```text
GOLD_V2_25B7_COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_AUDIT_ONLY_REPORT.md
gold_v2_25b7_input_audit.csv
gold_v2_25b7_config_file_audit.csv
gold_v2_25b7_condition_object_inventory.csv
gold_v2_25b7_condition_path_counts.csv
gold_v2_25b7_operator_value_matrix.csv
gold_v2_25b7_key_only_loss_matrix.csv
gold_v2_25b7_semantics_feasibility_matrix.csv
gold_v2_25b7_next_step_plan.csv
gold_v2_25b7_coreb_frozen_condition_object_semantics_summary.json
```

## Required review questions

```text
Do frozen rules contain non-key condition paths?
Which paths/operators/values were lost by key-only matching?
Do multiple condition signatures collapse to the same KEY_COLS tuple?
Is a later non-key-only dry-run possible without fitting target rows?
What remains blocked even after condition objects are inspected?
```

## Safety

CoreB remains blocked. Source mutation, source recovery execution, final signal, live hook, Discord, MT5, and AI remain off.

Expected status:

```text
COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED
```
