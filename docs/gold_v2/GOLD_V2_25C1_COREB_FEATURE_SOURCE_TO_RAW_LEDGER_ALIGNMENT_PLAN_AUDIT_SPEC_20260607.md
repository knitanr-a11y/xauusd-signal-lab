# GOLD V2 25C1 CoreB feature source to raw ledger alignment plan audit spec

Date: 2026-06-07
Step: `25C1_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY`
Mode: audit-only timestamp alignment planning

## Purpose

25C0 accepted a candidate feature source for later alignment planning:

```text
FX_OUTPUTS/gold_v2_coreb_combined_required_feature_snapshot_audit_only/gold_v2_coreb_combined_required_feature_snapshot.csv
```

25C1 profiles timestamp overlap between the feature source `time` column and the raw signal ledger `entry_time` column.

25C1 does not execute CoreB replay, does not compute same_count parity, does not mutate source artifacts, and does not unblock CoreB.

## Numbered request convention

When requesting uploads, use this format:

```text
00_不要_貼らなくてOK
01_必要_...
02_必要_...
03_必要_...
```

`00` is reserved for unnecessary files. Necessary files start at `01`.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c0_coreb_feature_source_candidate_review_audit_only/09_25c0_coreb_feature_source_candidate_review_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

From those it resolves:

```text
feature source candidate CSV
rr125_raw_signal_ledger.csv
```

## Outputs

```text
00_不要_25c1_file_request_list.csv
01_25c1_GOLD_V2_COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_AUDIT_ONLY_REPORT.md
02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json
03_25c1_input_audit.csv
04_25c1_feature_source_time_profile.csv
05_25c1_raw_ledger_time_profile.csv
06_25c1_time_overlap_matrix.csv
07_25c1_missing_time_samples.csv
08_25c1_alignment_gate_matrix.csv
09_25c1_next_step_plan.csv
```

## Safety

CoreB remains blocked. Source recovery execution, source mutation, final signal, live hook, Discord, MT5, and AI remain off.

Expected status:

```text
COREB_FEATURE_SOURCE_TO_RAW_LEDGER_ALIGNMENT_PLAN_COMPLETED_AUDIT_ONLY_ALIGNMENT_REVIEW_REQUIRED
```
