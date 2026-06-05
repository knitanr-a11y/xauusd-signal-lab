# GOLD V2 18D TIER2 source artifact candidate review audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18D_TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY`
Mode: audit-only

## Purpose

18D reviews the 18C TIER2 source artifact inventory and prioritizes candidate artifacts for a later content-inspection plan.

18D is metadata review only. It does not recover the TIER2 row-level source identity, does not open candidate contents to validate rows, does not reconstruct from OHLC, does not implement predicates, does not implement arbitration, does not evaluate OHLC, does not run replay, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited 18C outputs:

1. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_tier2_source_artifact_inventory_summary.json`
2. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_inventory_checks.csv`
3. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_tier2_source_artifact_inventory.csv`
4. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_candidate_review_plan.csv`
5. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_required_next_gates.csv`
6. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_blockers.csv`
7. `FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only/gold_v2_18c_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer a recovered row-level identity.

## Expected input state

18C must have status:

`TIER2_SOURCE_ARTIFACT_INVENTORY_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 18C state:

- inventory ready true
- inventory rows non-negative
- source recovery executed false
- implementation allowed false
- OHLC replay allowed false
- live enabled false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Review policy

18D may classify inventory rows using metadata only:

- `candidate_exact_source_rows_metadata`
- `candidate_manifest_match_metadata`
- `candidate_portfolio_ledger_metadata`
- `candidate_rule_or_reconciled_metadata`
- `supporting_lineage_metadata`
- `insufficient_summary_or_status_metadata`
- `other_supporting_metadata`

18D must not open the candidate source content to recover a row identity. It may only assign review priority for the later 18E content-inspection plan.

## Output folder

`FX_OUTPUTS/gold_v2_18d_tier2_source_artifact_candidate_review_audit_only`

## Main outputs

- `GOLD_V2_18D_TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md`
- `gold_v2_18d_tier2_source_artifact_candidate_review_summary.json`
- `gold_v2_18d_input_audit.csv`
- `gold_v2_18d_candidate_review_checks.csv`
- `gold_v2_18d_candidate_review_matrix.csv`
- `gold_v2_18d_priority_candidate_artifacts.csv`
- `gold_v2_18d_insufficient_artifacts.csv`
- `gold_v2_18d_required_next_gates.csv`
- `gold_v2_18d_blockers.csv`
- `gold_v2_18d_safety_matrix.csv`

## Success status

`TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means metadata-based candidate review is ready. It does not mean the TIER2 row-level source identity has been recovered.

## Stop conditions

Stop if:

- any required input is missing,
- 18C status is not expected,
- 18C checks or safety contain STOP,
- source recovery has already been executed,
- any review row enables implementation/live/final/external actions,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18D success, the next possible step is:

`18E_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY`

18E must remain plan/audit-only unless explicit content-inspection approval is separately provided.
