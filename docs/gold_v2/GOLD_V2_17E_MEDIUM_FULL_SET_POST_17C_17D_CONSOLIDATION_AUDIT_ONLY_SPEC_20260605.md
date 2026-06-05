# GOLD V2 17E MEDIUM full-set post 17C/17D consolidation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17E_MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

17E consolidates the MEDIUM component readiness after:

- TIER2_HVT candidate mapping / load-smoke chain through 13L
- 17C RANGE96_REFINED source-row reconciliation
- 17D VOL_TRMEAN32_REFINED source-row reconciliation

17E is a status consolidation and gate audit. It does not implement executable live rules, final signal, Discord notification, MT5 ordering, AI API calls, or live hooks.

## Source of truth

Use only audited outputs:

1. `FX_OUTPUTS/gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit/gold_v2_13l_load_smoke_summary.json`
2. `FX_OUTPUTS/gold_v2_17c_range96_refined_reconciliation_audit_only/gold_v2_17c_range96_reconciliation_summary.json`
3. `FX_OUTPUTS/gold_v2_17c_range96_refined_reconciliation_audit_only/gold_v2_17c_range96_candidate_source_freeze_preview.json`
4. `FX_OUTPUTS/gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only/gold_v2_17d_vol_trmean32_reconciliation_summary.json`
5. `FX_OUTPUTS/gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only/gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json`
6. `FX_OUTPUTS/gold_v2_17a_medium_full_set_source_arbitration_audit_only/gold_v2_17a_medium_arbitration_matrix.csv`
7. `FX_OUTPUTS/gold_v2_17b_medium_non_tier2_component_replay_planning_audit_only/gold_v2_17b_replay_planning_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer live rules from summaries.

## Expected component state

### TIER2_HVT

Expected 13L status:

`MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_PASSED`

This means candidate mapping/load-smoke is ready, but not final signal.

### RANGE96_REFINED

Expected 17C status:

`RANGE96_REFINED_SOURCE_RECONCILIATION_READY_FOR_CANDIDATE_SOURCE_FREEZE_AUDIT_ONLY`

Expected counts:

- `rule_ledger_rows = 51`
- `combined_ledger_rows = 117`

### VOL_TRMEAN32_REFINED

Expected 17D status:

`VOL_TRMEAN32_REFINED_SOURCE_RECONCILIATION_READY_FOR_CANDIDATE_SOURCE_FREEZE_AUDIT_ONLY`

Expected counts:

- `rule_ledger_rows = 36`
- `combined_ledger_rows = 104`

## Output folder

`FX_OUTPUTS/gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only`

## Main output files

- `GOLD_V2_17E_MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_17e_medium_full_set_consolidation_summary.json`
- `gold_v2_17e_input_audit.csv`
- `gold_v2_17e_component_status_matrix.csv`
- `gold_v2_17e_readiness_checks.csv`
- `gold_v2_17e_next_steps.csv`
- `gold_v2_17e_blockers.csv`
- `gold_v2_17e_safety_matrix.csv`

## Audit method

1. Confirm all required input artifacts exist.
2. Confirm 13L TIER2_HVT status is the expected passed status.
3. Confirm 17C RANGE96 status, expected counts, safety flags, and no missing keys.
4. Confirm 17D VOL_TRMEAN32 status, expected counts, safety flags, and no missing keys.
5. Confirm 17A/17B still contain the expected component rows and statuses.
6. Build a full MEDIUM component status matrix.
7. Write blockers and next steps.

## Success condition

17E succeeds when all source statuses and counts pass and every safety flag remains false.

Success status:

`MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED`

This status means the MEDIUM full-set reconciliation state is consolidated, not that live trading is allowed.

## Stop conditions

Stop with non-zero exit if:

- Any required artifact is missing.
- 13L, 17C, or 17D status does not match expectation.
- 17C/17D expected counts do not match.
- Any safety flag is not false.
- Any final signal / Discord / MT5 / AI API / live hook path appears enabled.

## AI API usage

AI API is not called.

## Do not run / do not enable

Do not enable final signal, Discord, MT5, AI API, live hook, or NO_SIGNAL notification from this step.

## Recommended next work after success

After 17E success, the next work may be a separate audit-only step for MEDIUM full-set candidate mapping/load-smoke design. That later step must still keep final signal and all external actions disabled.
