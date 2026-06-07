# GOLD V2 25C29 CoreB G1 narrowing candidate review audit spec

Date: 2026-06-07
Step: `25C29_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY`
Mode: audit-only candidate review

## Purpose

25C28 produced a plan-only narrowing candidate set. 25C29 reviews that set before any narrowed replay execution.

This step does not change CoreB conditions and does not run a narrowed replay.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only/02_25c28_coreb_g1_filter_narrowing_plan_summary.json
FX_OUTPUTS/gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only/04_25c28_narrowing_candidate_matrix.csv
FX_OUTPUTS/gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only/05_25c28_boundary_matrix.csv
FX_OUTPUTS/gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only/06_25c28_acceptance_gate_matrix.csv
FX_OUTPUTS/gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only/07_25c28_next_step_plan.csv
```

## Outputs

```text
00_不要_25c29_file_request_list.csv
01_25c29_GOLD_V2_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
02_25c29_coreb_g1_narrowing_candidate_review_summary.json
03_25c29_input_audit.csv
04_25c29_candidate_review_matrix.csv
05_25c29_candidate_action_summary.csv
06_25c29_execution_readiness_gate_matrix.csv
07_25c29_next_step_plan.csv
```

Expected status:

```text
COREB_G1_NARROWING_CANDIDATE_REVIEW_COMPLETED_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_NARROWED_DRY_RUN
```
