# GOLD V2 18N TIER2 source identity dry-run reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

18N reconciles 18M content-audit outputs against the 18K dry-run ledger and 18L load-smoke outputs.

18N is still audit-only. It must not promote any ledger or distribution to source-of-truth. It must not execute source recovery, finalize source identity, recover source identity, implement live/final evaluator behavior, replay OHLC, send Discord notifications, send NO_SIGNAL Discord notifications, place MT5 orders, call AI APIs, or call live hooks.

## Upstream requirements

18N must stop unless 18M summary status is:

`TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18N must also stop unless all 18M STOP counts are zero and all 18M safety flags remain blocked.

## Inputs

18M outputs from:

`FX_OUTPUTS/gold_v2_18m_tier2_source_identity_dry_run_content_audit_only`

- `gold_v2_18m_tier2_source_identity_dry_run_content_summary.json`
- `gold_v2_18m_input_audit.csv`
- `gold_v2_18m_content_checks.csv`
- `gold_v2_18m_required_field_completeness.csv`
- `gold_v2_18m_value_domain_audit.csv`
- `gold_v2_18m_row_identity_integrity_audit.csv`
- `gold_v2_18m_distribution_by_artifact_role.csv`
- `gold_v2_18m_distribution_by_component.csv`
- `gold_v2_18m_distribution_by_direction.csv`
- `gold_v2_18m_distribution_by_outcome.csv`
- `gold_v2_18m_distribution_by_source_status.csv`
- `gold_v2_18m_required_next_gates.csv`
- `gold_v2_18m_blockers.csv`
- `gold_v2_18m_safety_matrix.csv`
- `GOLD_V2_18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY_REPORT.md`

18L summary from:

`FX_OUTPUTS/gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only/gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json`

18K inputs from:

`FX_OUTPUTS/gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only`

- `gold_v2_18k_dry_run_candidate_identity_rows.csv`
- `gold_v2_18k_artifact_row_counts.csv`
- `gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json`

## Reconciliation checks

18N checks:

- 18M status and 18M STOP counts
- 18M row count equals 18K ledger row count and expected 104
- 18K artifact count equals expected 5
- 18K expected and actual artifact row sums equal 104
- 18M distribution by artifact role matches the 18K ledger recomputation
- 18M distribution by component matches the 18K ledger recomputation
- 18M distribution by direction matches the 18K ledger recomputation
- 18M distribution by outcome matches the 18K ledger recomputation
- 18M distribution by source status matches the 18K ledger recomputation
- 18M content, field, value-domain, row-identity, and safety audits have zero STOP rows
- source recovery, identity finalization, recovered, OHLC replay, live/final, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain false
- next gates still block source recovery, source finalization, live, and final signal

## Output folder

`FX_OUTPUTS/gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only`

## Outputs

- `GOLD_V2_18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json`
- `gold_v2_18n_input_audit.csv`
- `gold_v2_18n_reconciliation_checks.csv`
- `gold_v2_18n_distribution_reconciliation.csv`
- `gold_v2_18n_row_count_reconciliation.csv`
- `gold_v2_18n_upstream_stop_audit.csv`
- `gold_v2_18n_required_next_gates.csv`
- `gold_v2_18n_blockers.csv`
- `gold_v2_18n_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that 18M outputs reconcile with 18K/18L audit-only outputs. It does not mean source recovery, source identity finalization, source identity recovery, source-of-truth acceptance, live readiness, or final signal readiness.

## Required next gate

`18O_TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_AUDIT_ONLY`

18O may review blockers and decide what evidence is still missing. 18O must still not enable source recovery, identity finalization, live/final behavior, Discord, MT5, AI API, live hooks, or NO_SIGNAL Discord.

## BAT execution order

1. Confirm 18K, 18L, and 18M outputs exist.
2. Run `scripts\gold_v2_runtime\bat\18N_AUDIT_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY.bat`.
3. Review reconciliation checks, distribution reconciliation, row-count reconciliation, safety matrix, summary, and report.

## Stop conditions

18N stops if required inputs are missing, 18M did not pass, any upstream STOP row is present, distributions do not reconcile, row counts do not reconcile, any forbidden safety flag becomes true, or any output is promoted to source-of-truth.
