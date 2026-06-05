# GOLD V2 18M TIER2 source identity dry-run content audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

18M performs a content audit of the 18K dry-run candidate identity ledger after 18L load-smoke passed.

18M does not promote the ledger to source-of-truth. 18M does not execute source recovery, finalize source identity, recover source identity, implement live/final evaluator behavior, replay OHLC, send Discord notifications, send NO_SIGNAL Discord notifications, place MT5 orders, call AI APIs, or call live hooks.

## Upstream requirements

18M must stop unless the 18L summary status is:

`TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18M must also stop unless all 18L STOP counts are zero.

## Inputs

18L inputs from:

`FX_OUTPUTS/gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only`

- `gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json`
- `gold_v2_18l_input_audit.csv`
- `gold_v2_18l_load_checks.csv`
- `gold_v2_18l_ledger_column_audit.csv`
- `gold_v2_18l_ledger_safety_audit.csv`
- `gold_v2_18l_row_count_audit.csv`
- `gold_v2_18l_required_next_gates.csv`
- `gold_v2_18l_blockers.csv`
- `gold_v2_18l_safety_matrix.csv`
- `GOLD_V2_18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

18K ledger input from:

`FX_OUTPUTS/gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only/gold_v2_18k_dry_run_candidate_identity_rows.csv`

## Content checks

18M checks the ledger content only:

- row count is 104
- required identity fields are present and non-empty where required
- `tp` and `sl` are allowed to be empty because 18K must not recalculate them from OHLC
- `source_row_index0` and `source_row_number_1based` are internally consistent
- every `source_row_hash` starts with `dryrun_sha256:`
- `source_row_hash` values are unique within the 18K ledger
- `ledger_label` remains `DRY_RUN_CANDIDATE_IDENTITY_LEDGER_NOT_SOURCE_OF_TRUTH`
- `dry_run_status` remains `DRY_RUN_CANDIDATE_ONLY_NOT_SOURCE_OF_TRUTH`
- `source_row_hash_scope` remains `DRY_RUN_CANDIDATE_ONLY_NOT_FINAL_SOURCE_IDENTITY`
- `direction` is non-empty and one of BUY or SELL
- `outcome` is non-empty and in the allowed audit-only outcome set
- all source recovery, finalization, recovered, live/final, OHLC replay, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord flags remain false

18M may produce distribution summaries by artifact role, component, direction, outcome, and source status. These summaries are audit-only and must not be used as source-of-truth acceptance.

## Output folder

`FX_OUTPUTS/gold_v2_18m_tier2_source_identity_dry_run_content_audit_only`

## Outputs

- `GOLD_V2_18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY_REPORT.md`
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

## Success status

`TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that 18K ledger content passed audit-only checks. It does not mean source recovery, source identity finalization, source identity recovery, source-of-truth acceptance, live readiness, or final signal readiness.

## Required next gate

`18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY`

18N may reconcile content-audit summaries against earlier audit expectations. 18N must still not enable source recovery, identity finalization, live/final behavior, Discord, MT5, AI API, live hooks, or NO_SIGNAL Discord.

## BAT execution order

1. Confirm 18K and 18L outputs exist.
2. Run `scripts\gold_v2_runtime\bat\18M_AUDIT_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY.bat`.
3. Review content checks, required field completeness, value domain audit, row identity integrity audit, distributions, safety matrix, summary, and report.

## Stop conditions

18M stops if required inputs are missing, 18L did not pass, any 18L STOP count is non-zero, the ledger row count is not 104, required fields are missing or unexpectedly empty, value domains fail, row identity integrity fails, forbidden flags become true, or the ledger is marked source-of-truth.
