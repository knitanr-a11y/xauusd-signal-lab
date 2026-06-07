# GOLD V2 25C22 CoreB entry grain contract review audit spec

Date: 2026-06-07
Step: `25C22_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY`
Mode: audit-only contract review, no dry-run execution

## Purpose

25C21 proposed candidate grains:

```text
G1: dataset + entry_time + policy
G2: dataset + entry_time + policy + filter_family
G3: dataset + entry_time + policy + filter
```

25C22 reviews G1/G2 and selects the safer next audit contract. It does not change CoreB conditions and does not execute a dry-run.

## Outputs

```text
00_不要_25c22_file_request_list.csv
01_25c22_GOLD_V2_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c22_coreb_entry_grain_contract_review_summary.json
03_25c22_input_audit.csv
04_25c22_grain_contract_review_matrix.csv
05_25c22_selected_grain_contract.csv
06_25c22_grain_contract_decision_matrix.csv
07_25c22_next_step_plan.csv
```

Expected status:

```text
COREB_ENTRY_GRAIN_CONTRACT_REVIEW_COMPLETED_AUDIT_ONLY_G1_ENTRY_LEVEL_REVIEW_SELECTED
```
