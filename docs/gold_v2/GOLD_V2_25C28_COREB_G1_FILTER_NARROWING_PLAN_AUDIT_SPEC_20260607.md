# GOLD V2 25C28 CoreB G1 filter narrowing plan audit spec

Date: 2026-06-07
Step: `25C28_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY`
Mode: audit-only plan

## Purpose

25C27 identified replay-side filter overlap as the dominant G1 left-only driver.

25C28 prepares a read-only narrowing plan. It does not change rule conditions and does not run another replay.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only/02_25c27_coreb_g1_left_only_replay_filter_contract_summary.json
FX_OUTPUTS/gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only/04_25c27_replay_filter_driver_matrix.csv
FX_OUTPUTS/gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only/05_25c27_replay_filter_family_contract_matrix.csv
FX_OUTPUTS/gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only/06_25c27_replay_overlap_risk_matrix.csv
FX_OUTPUTS/gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only/07_25c27_replay_filter_contract_decision_matrix.csv
```

## Outputs

```text
00_不要_25c28_file_request_list.csv
01_25c28_GOLD_V2_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY_REPORT.md
02_25c28_coreb_g1_filter_narrowing_plan_summary.json
03_25c28_input_audit.csv
04_25c28_narrowing_candidate_matrix.csv
05_25c28_boundary_matrix.csv
06_25c28_acceptance_gate_matrix.csv
07_25c28_next_step_plan.csv
```

Expected status:

```text
COREB_G1_FILTER_NARROWING_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED
```
