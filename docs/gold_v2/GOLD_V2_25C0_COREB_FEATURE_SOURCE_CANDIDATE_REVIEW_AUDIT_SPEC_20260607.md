# GOLD V2 25C0 CoreB feature source candidate review audit spec

Date: 2026-06-07
Step: `25C0_COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY`
Mode: audit-only candidate review, no replay execution

## Purpose

25B9 discovered a complete table candidate for the 38 CoreB condition-object fields:

```text
FX_OUTPUTS/gold_v2_coreb_combined_required_feature_snapshot_audit_only/gold_v2_coreb_combined_required_feature_snapshot.csv
```

25C0 profiles that table candidate and decides whether it can be considered a candidate feature source for a later non-key-only dry-run plan.

25C0 does not execute CoreB replay, does not compute same_count parity, does not mutate sources, and does not unblock CoreB.

## Numbered output convention

Starting from 25C0, output artifacts use numeric prefixes to reduce confusion:

```text
00_ report
01_ input audit
02_ candidate selection
03_ schema profile
04_ feature value profile
05_ time key profile
06_ acceptance gates
07_ file request list
08_ next step plan
09_ summary json
```

## Inputs

25C0 reads:

```text
Files/FX_OUTPUTS/gold_v2_25b9_coreb_feature_source_discovery_audit_only/gold_v2_25b9_coreb_feature_source_discovery_summary.json
Files/FX_OUTPUTS/gold_v2_25b9_coreb_feature_source_discovery_audit_only/gold_v2_25b9_feature_coverage_by_candidate.csv
Files/FX_OUTPUTS/gold_v2_25b9_coreb_feature_source_discovery_audit_only/gold_v2_25b9_feature_source_candidate_inventory.csv
Files/FX_OUTPUTS/gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only/gold_v2_25b8_required_feature_manifest.csv
```

It selects complete `table_candidate` rows first and profiles the best candidate.

## Required outputs

```text
00_GOLD_V2_25C0_COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
01_25c0_input_audit.csv
02_25c0_candidate_selection.csv
03_25c0_candidate_schema_profile.csv
04_25c0_required_feature_value_profile.csv
05_25c0_time_key_profile.csv
06_25c0_source_acceptance_gate_matrix.csv
07_25c0_file_request_list.csv
08_25c0_next_step_plan.csv
09_25c0_coreb_feature_source_candidate_review_summary.json
```

## Review gates

25C0 checks:

```text
candidate exists
candidate is table_candidate
candidate covers all 38 required fields
candidate has time column
candidate has no duplicate time rows or flags them
candidate has numeric, non-empty required feature fields
candidate has row count and time range
candidate remains audit-only
```

## Safety

CoreB remains blocked. Source recovery execution, source mutation, final signal, live hook, Discord, MT5, and AI remain off.

Expected status:

```text
COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_COMPLETED_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED
```
