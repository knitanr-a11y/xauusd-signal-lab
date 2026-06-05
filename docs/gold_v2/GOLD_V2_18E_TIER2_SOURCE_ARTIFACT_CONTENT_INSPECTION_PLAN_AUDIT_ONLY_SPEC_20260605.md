# GOLD V2 18E TIER2 source artifact content inspection plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18E_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

18E plans how to inspect the prioritized TIER2 candidate artifacts selected by 18D.

18E is planning only. It does not inspect candidate file contents, does not recover the TIER2 row-level source identity, does not reconstruct from OHLC, does not implement predicates, does not implement arbitration, does not evaluate OHLC, does not run replay, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited 18D outputs:

1. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_tier2_source_artifact_candidate_review_summary.json`
2. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_candidate_review_checks.csv`
3. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_candidate_review_matrix.csv`
4. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_priority_candidate_artifacts.csv`
5. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_insufficient_artifacts.csv`
6. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_required_next_gates.csv`
7. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_blockers.csv`
8. `FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only/gold_v2_18d_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer a recovered row-level identity.

## Expected input state

18D must have status:

`TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 18D state:

- candidate review ready true
- review rows 90
- priority candidate rows 13
- insufficient rows 7
- content inspection allowed now false
- source recovery executed false
- implementation allowed false
- OHLC replay allowed false
- live enabled false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Planning policy

18E may create a content-inspection plan for priority candidates. It must not inspect file contents yet.

18E must define:

- planned inspection order,
- allowed read-only inspection method,
- required row-level identity fields,
- validation checks,
- hard stop conditions,
- non-enablement safety checks,
- required authorization gate before any content inspection execution.

No plan row may mark content inspection, source recovery, implementation, live, final, or external actions as allowed now.

## Output folder

`FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only`

## Main outputs

- `GOLD_V2_18E_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_18e_tier2_source_artifact_content_inspection_plan_summary.json`
- `gold_v2_18e_input_audit.csv`
- `gold_v2_18e_content_inspection_plan_checks.csv`
- `gold_v2_18e_selected_priority_artifacts.csv`
- `gold_v2_18e_content_inspection_plan.csv`
- `gold_v2_18e_required_identity_validation_fields.csv`
- `gold_v2_18e_stop_conditions.csv`
- `gold_v2_18e_required_next_gates.csv`
- `gold_v2_18e_blockers.csv`
- `gold_v2_18e_safety_matrix.csv`

## Success status

`TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means the inspection plan exists. It does not mean content inspection has been executed or the TIER2 row-level source identity has been recovered.

## Stop conditions

Stop if:

- any required input is missing,
- 18D status is not expected,
- 18D checks or safety contain STOP,
- content inspection was already allowed/executed,
- source recovery was already executed,
- any plan row enables content inspection/source recovery/implementation/live/final/external actions,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18E success, the next possible step is:

`18F_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY`

18F must remain an authorization gate/audit-only step and must not inspect content unless explicit approval is separately provided.
