# GOLD V2 25C11 CoreB filter replay result review audit spec

Date: 2026-06-07
Step: `25C11_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY`
Mode: audit-only result review, no replay execution

## Purpose

25C10 executed filter-specific diagnostic replay and still showed large filter-level mismatches:

```text
filter_level_both = 849
filter_level_left_only = 4444
filter_level_right_only = 1544
```

25C11 reviews the result by policy and filter contract to identify the next audit target. It does not change CoreB conditions and does not unblock CoreB.

## Review focus

25C11 must identify:

```text
1. policies present in signal but absent/missing in target comparison
2. policies present in target but absent in signal comparison
3. filters with highest left_only over-generation
4. filters with highest right_only missing target rows
5. whether mismatch is contract/source-policy mapping issue or CoreB condition issue
```

## Inputs

```text
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/05_25c10_filter_level_compare_matrix.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/06_25c10_filter_compare_by_contract.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/09_25c10_replay_gate_matrix.csv
```

## Outputs

```text
00_不要_25c11_file_request_list.csv
01_25c11_GOLD_V2_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c11_coreb_filter_replay_result_review_summary.json
03_25c11_input_audit.csv
04_25c11_policy_signal_target_matrix.csv
05_25c11_filter_contract_match_rate_matrix.csv
06_25c11_top_overgenerated_contracts.csv
07_25c11_top_missing_contracts.csv
08_25c11_result_decision_matrix.csv
09_25c11_next_step_plan.csv
```

## Safety

CoreB remains blocked. This is not source recovery. No mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_FILTER_REPLAY_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_POLICY_MAPPING_REVIEW_REQUIRED
```
