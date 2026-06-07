# GOLD V2 25C27 CoreB G1 left-only replay filter contract audit spec

Date: 2026-06-07
Step: `25C27_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY`
Mode: audit-only contract review

## Purpose

25C26 showed that G1 left-only entries are dominated by replay-side filter overlap, especially the same_count plus unique_origins family.

25C27 reviews the replay-side filter contract only. It does not change CoreB conditions and does not enable live evaluation.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c26_coreb_g1_left_only_root_cause_audit_only/02_25c26_coreb_g1_left_only_root_cause_summary.json
FX_OUTPUTS/gold_v2_25c26_coreb_g1_left_only_root_cause_audit_only/04_25c26_left_only_filter_family_profile.csv
FX_OUTPUTS/gold_v2_25c26_coreb_g1_left_only_root_cause_audit_only/05_25c26_left_only_signal_multiplicity_profile.csv
FX_OUTPUTS/gold_v2_25c26_coreb_g1_left_only_root_cause_audit_only/06_25c26_left_only_sample_enrichment.csv
```

## Outputs

```text
00_不要_25c27_file_request_list.csv
01_25c27_GOLD_V2_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY_REPORT.md
02_25c27_coreb_g1_left_only_replay_filter_contract_summary.json
03_25c27_input_audit.csv
04_25c27_replay_filter_driver_matrix.csv
05_25c27_replay_filter_family_contract_matrix.csv
06_25c27_replay_overlap_risk_matrix.csv
07_25c27_replay_filter_contract_decision_matrix.csv
08_25c27_next_step_plan.csv
```

Expected status:

```text
COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_COMPLETED_AUDIT_ONLY_FILTER_NARROWING_PLAN_REQUIRED
```
