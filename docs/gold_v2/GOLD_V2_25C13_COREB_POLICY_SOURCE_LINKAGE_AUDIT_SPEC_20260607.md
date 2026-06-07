# GOLD V2 25C13 CoreB policy source linkage audit spec

Date: 2026-06-07
Step: `25C13_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY`
Mode: audit-only config linkage review

## Purpose

25C12 showed a policy mapping gap:

```text
RR125_from_ALL_BUY_rules exists in raw/target rows but has no replay rows.
RR125_from_RR1_rules has many replay rows compared with target rows.
```

25C13 reviews frozen CoreB config artifacts and traces policy tokens and linkage markers. It does not modify CoreB logic and does not enable CoreB.

## Outputs

```text
00_不要_25c13_file_request_list.csv
01_25c13_GOLD_V2_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY_REPORT.md
02_25c13_coreb_policy_source_linkage_summary.json
03_25c13_input_audit.csv
04_25c13_config_policy_token_inventory.csv
05_25c13_config_policy_path_samples.csv
06_25c13_pipeline_config_linkage_matrix.csv
07_25c13_policy_source_linkage_decision_matrix.csv
08_25c13_next_step_plan.csv
```

Expected status:

```text
COREB_POLICY_SOURCE_LINKAGE_AUDIT_COMPLETED_AUDIT_ONLY_SELECTED_POLICY_ASSIGNMENT_REVIEW_REQUIRED
```
