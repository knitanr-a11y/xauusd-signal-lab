# GOLD V2 25C12 CoreB policy mapping audit spec

Date: 2026-06-07
Step: `25C12_COREB_POLICY_MAPPING_AUDIT_ONLY`
Mode: audit-only review

## Purpose

25C11 showed that `RR125_from_ALL_BUY_rules` appears in target rows but not in replay signals, while `RR125_from_RR1_rules` produces many extra replay rows.

25C12 traces policy counts across available audited artifacts:

```text
raw rows
condition count rows
selected hit rows
filter replay rows
target rows
```

It does not modify CoreB logic and does not enable CoreB.

## Outputs

```text
00_不要_25c12_file_request_list.csv
01_25c12_GOLD_V2_COREB_POLICY_MAPPING_AUDIT_ONLY_REPORT.md
02_25c12_coreb_policy_mapping_summary.json
03_25c12_input_audit.csv
04_25c12_policy_pipeline_coverage_matrix.csv
05_25c12_all_buy_gap_trace_matrix.csv
06_25c12_rr1_overgeneration_trace_matrix.csv
07_25c12_policy_filter_contract_matrix.csv
08_25c12_policy_mapping_decision_matrix.csv
09_25c12_next_step_plan.csv
```

Expected status:

```text
COREB_POLICY_MAPPING_AUDIT_COMPLETED_AUDIT_ONLY_SOURCE_POLICY_REVIEW_REQUIRED
```
