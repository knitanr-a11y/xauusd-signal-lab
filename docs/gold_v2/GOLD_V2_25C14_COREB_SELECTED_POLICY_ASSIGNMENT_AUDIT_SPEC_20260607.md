# GOLD V2 25C14 CoreB selected policy assignment audit spec

Date: 2026-06-07
Step: `25C14_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY`
Mode: audit-only selected policy assignment review

## Purpose

25C13 showed that both policies appear in frozen config text, but the policy roles differ by section.

25C14 reviews the selected-policy assignment directly:

```text
selected_rules
same_count_source_rules
source_universe_rules
source_rule_conditions
```

It does not modify CoreB logic and does not enable CoreB.

## Outputs

```text
00_不要_25c14_file_request_list.csv
01_25c14_GOLD_V2_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY_REPORT.md
02_25c14_coreb_selected_policy_assignment_summary.json
03_25c14_input_audit.csv
04_25c14_section_policy_count_matrix.csv
05_25c14_selected_rule_policy_matrix.csv
06_25c14_source_rule_policy_matrix.csv
07_25c14_assignment_gap_decision_matrix.csv
08_25c14_next_step_plan.csv
```

Expected status:

```text
COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_COMPLETED_AUDIT_ONLY_SELECTED_RULE_POLICY_GAP_CONFIRMED
```
