# GOLD V2 25C21 CoreB entry grain contract plan audit spec

Date: 2026-06-07
Step: `25C21_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY`
Mode: audit-only contract plan, no dry-run execution

## Purpose

25C20 showed that mismatch remains after reviewing filter-family and entry_time grain:

```text
filter_family_left_only = 1807
filter_family_right_only = 192
entry_grain_left_only = 813
entry_grain_right_only = 78
```

25C21 defines candidate comparison grains before any further execution.

## Candidate grains

```text
G1: dataset + entry_time + policy
G2: dataset + entry_time + policy + filter_family
G3: dataset + entry_time + policy + filter
```

No CoreB condition is changed. No replay execution is performed.

## Outputs

```text
00_不要_25c21_file_request_list.csv
01_25c21_GOLD_V2_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY_REPORT.md
02_25c21_coreb_entry_grain_contract_plan_summary.json
03_25c21_input_audit.csv
04_25c21_entry_grain_candidate_matrix.csv
05_25c21_grain_selection_boundary_matrix.csv
06_25c21_acceptance_gate_matrix.csv
07_25c21_next_step_plan.csv
```

Expected status:

```text
COREB_ENTRY_GRAIN_CONTRACT_PLAN_READY_AUDIT_ONLY_DRY_RUN_EXECUTION_BLOCKED
```
