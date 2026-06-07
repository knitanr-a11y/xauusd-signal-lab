# GOLD V2 25B3 CoreB source shortlist content audit spec

Date: 2026-06-07
Step: `25B3_COREB_SOURCE_SHORTLIST_CONTENT_AUDIT_ONLY`
Mode: audit-only content/schema/linkage inspection

## 1. Purpose

25B2 narrowed the 25B candidate inventory from 430 rows to a priority shortlist of 6 files.

25B3 inspects only those 6 shortlisted files and records their content, schema, config keys, and linkage relationship.

25B3 must not reconstruct `same_count`, replay CoreB, infer membership, fit `cluster_id`, or enable any live/final action.

## 2. Source-of-truth inputs

25B3 uses the 25B2 outputs as source-of-truth inputs:

```text
Files/FX_OUTPUTS/gold_v2_25b2_coreb_cluster_candidate_triage_audit_only/gold_v2_25b2_priority_shortlist.csv
Files/FX_OUTPUTS/gold_v2_25b2_coreb_cluster_candidate_triage_audit_only/gold_v2_25b2_coreb_cluster_candidate_triage_summary.json
```

Expected shortlist size from the uploaded 25B2 run:

```text
priority_shortlist_rows = 6
```

The shortlisted files are expected to include:

```text
gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv
configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json
configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json
gold_v2_rr125_second_core_probe_outputs/rr125_top_ledgers.csv
```

## 3. Output folder

```text
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/
```

## 4. Required outputs

```text
GOLD_V2_25B3_COREB_SOURCE_SHORTLIST_CONTENT_AUDIT_ONLY_REPORT.md
gold_v2_25b3_input_audit.csv
gold_v2_25b3_shortlist_file_content_audit.csv
gold_v2_25b3_csv_profile.csv
gold_v2_25b3_json_key_inventory.csv
gold_v2_25b3_coreb_source_linkage_matrix.csv
gold_v2_25b3_unblock_gap_matrix.csv
gold_v2_25b3_next_review_plan.csv
gold_v2_25b3_coreb_source_shortlist_content_summary.json
```

## 5. What 25B3 records

For CSV files:

```text
row_count
column_count
columns
sha256
key field coverage
dataset/policy/direction/rr_bucket counts when present
same_count / cluster_id coverage when present
```

For JSON files:

```text
sha256
top-level keys
selected status fields
flattened key/value inventory for audit review
links to other source files, if present
```

For all files:

```text
whether the file is source universe, frozen rule config, combined evaluator definition, or target top ledger
whether the file itself proves row-level membership semantics
whether CoreB live evaluator can be unblocked now
```

## 6. Unblock policy

25B3 must keep:

```text
coreb_live_evaluator_unblocked = false
replay_executed = false
same_count_exact_parity_proven = false
cluster_membership_parity_proven = false
```

A file can be useful for review without proving membership parity.

## 7. Stop conditions

25B3 stops if:

```text
25B2 priority shortlist is missing
25B2 summary is missing
shortlist row count does not match 25B2 summary priority_shortlist_rows
required shortlist columns are missing
any shortlisted file is missing
any safety flag would be enabled
```

## 8. Safety flags

All outputs must keep:

```text
source_recovery_execution_allowed_now = false
source_mutation_allowed = false
source_identity_finalization_allowed_now = false
live_evaluator_final_signal_allowed = false
final_signal_allowed = false
discord_send_allowed = false
mt5_order_allowed = false
ai_api_allowed = false
live_hook_allowed = false
no_signal_discord_notification_allowed = false
old_gold_disc8_quarantined = true
source_recovery_chain_status = PAUSED_AT_24AF
```

## 9. Next work after 25B3

If 25B3 confirms the raw signal ledger and frozen configs are readable and linked, the next safe step is a replay plan only, not replay execution:

```text
25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY
```

25B4 would specify how to attempt exact replay later, including required inputs, expected 125 rows, missing/extra key checks, same_count exact match checks, and membership parity checks.
