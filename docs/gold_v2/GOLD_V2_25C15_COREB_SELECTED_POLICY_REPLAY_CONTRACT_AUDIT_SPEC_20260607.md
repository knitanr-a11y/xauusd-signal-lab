# GOLD V2 25C15 CoreB selected policy replay contract audit spec

Date: 2026-06-07
Step: `25C15_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY`
Mode: audit-only contract definition

## Purpose

25C14 confirmed the selected-policy assignment gap:

```text
selected ALL_BUY rows = 0
selected RR1 rows = 12
source ALL_BUY rows = 42
source RR1 rows = 36
```

25C15 defines the replay contract that preserves this role split:

```text
selected output policy scope: policies present in selected-side rule sections
source count policy scope: policies present in source-side rule sections
target handling: policies outside selected output scope are not direct selected-output targets
```

It does not run replay, modify CoreB logic, or enable CoreB.

## Outputs

```text
00_不要_25c15_file_request_list.csv
01_25c15_GOLD_V2_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY_REPORT.md
02_25c15_coreb_selected_policy_replay_contract_summary.json
03_25c15_input_audit.csv
04_25c15_selected_policy_scope_contract.csv
05_25c15_source_universe_policy_scope_contract.csv
06_25c15_target_policy_handling_contract.csv
07_25c15_replay_contract_decision_matrix.csv
08_25c15_next_step_plan.csv
```

Expected status:

```text
COREB_SELECTED_POLICY_REPLAY_CONTRACT_DEFINED_AUDIT_ONLY_TARGET_SCOPE_REVIEW_REQUIRED
```
