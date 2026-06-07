# GOLD V2 25C9 CoreB target filter contract replay plan audit spec

Date: 2026-06-07
Step: `25C9_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY`
Mode: audit-only replay planning, no execution

## Purpose

25C8 showed that target comparison is not a single contract. The target ledger contains multiple filter contracts:

```text
same_count>=8
same_count>=10
same_count>=15
same_count>=20
unique_origins>=2
unique_origins>=3
same_count>=N&unique_origins>=M
```

25C9 builds a filter-specific replay plan without changing CoreB conditions and without executing any replay.

## Key principle

The current 25C5 diagnostic signal contract is only:

```text
selected_hit_by_entry_time AND source_count_by_entry_time >= 15
```

It cannot be directly compared to all target filter rows. Filter-specific replay plans must use the target filter's own threshold/dimension:

```text
same_count threshold: source_count_by_entry_time >= N
unique origins threshold: unique_origin_count_by_entry_time >= M
```

## Inputs

```text
FX_OUTPUTS/gold_v2_25c8_coreb_mismatch_root_cause_audit_only/02_25c8_coreb_mismatch_root_cause_summary.json
FX_OUTPUTS/gold_v2_25c8_coreb_mismatch_root_cause_audit_only/04_25c8_target_filter_inventory.csv
FX_OUTPUTS/gold_v2_25c8_coreb_mismatch_root_cause_audit_only/07_25c8_threshold_filter_alignment_matrix.csv
```

## Outputs

```text
00_不要_25c9_file_request_list.csv
01_25c9_GOLD_V2_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY_REPORT.md
02_25c9_coreb_target_filter_contract_replay_plan_summary.json
03_25c9_input_audit.csv
04_25c9_filter_contract_plan.csv
05_25c9_replay_variant_matrix.csv
06_25c9_required_metric_matrix.csv
07_25c9_acceptance_gate_matrix.csv
08_25c9_forbidden_methods.csv
09_25c9_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED
```
