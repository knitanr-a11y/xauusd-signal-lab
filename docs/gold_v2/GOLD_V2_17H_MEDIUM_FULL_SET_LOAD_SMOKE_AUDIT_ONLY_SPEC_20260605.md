# GOLD V2 17H MEDIUM full-set load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17H_MEDIUM_FULL_SET_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

17H load-smokes the 17G MEDIUM full-set candidate manifest.

The goal is to prove that the manifest can be loaded and checked for structural integrity before any later dry-run gate design. It is not an executable signal evaluator and it does not enable final signal, Discord, MT5, AI API, or live hooks.

## Source of truth

Use only 17G audited outputs:

1. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_medium_full_set_candidate_mapping_summary.json`
2. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`
3. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_component_counts.csv`
4. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_mapping_checks.csv`
5. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer RANGE96/VOL predicates or TIER2 row identities.

## Expected state

17G must have status:

`MEDIUM_FULL_SET_CANDIDATE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected manifest counts:

- total rows: 309
- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140

Expected manifest columns:

- `manifest_row_id`
- `component`
- `source_step`
- `source_identity_type`
- `source_role`
- `source_row_number_1based`
- `source_key`
- `strategy_id`
- `source_row_hash`
- `source_status`
- `live_executable`
- `final_signal_allowed`

## Load-smoke checks

17H verifies:

1. all inputs exist,
2. 17G summary status is expected,
3. 17G mapping checks and safety matrix contain no `STOP`,
4. manifest columns are present,
5. total and per-component row counts match,
6. `manifest_row_id` is non-empty and unique,
7. `source_row_hash` is non-empty,
8. all `live_executable` values are false,
9. all `final_signal_allowed` values are false,
10. TIER2 remains a `13L_SUMMARY_CHAIN_REFERENCE`,
11. RANGE96/VOL rows remain `SOURCE_ROW_HASH` identities.

## Output folder

`FX_OUTPUTS/gold_v2_17h_medium_full_set_load_smoke_audit_only`

## Main outputs

- `GOLD_V2_17H_MEDIUM_FULL_SET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_17h_medium_full_set_load_smoke_summary.json`
- `gold_v2_17h_input_audit.csv`
- `gold_v2_17h_manifest_load_checks.csv`
- `gold_v2_17h_component_counts_check.csv`
- `gold_v2_17h_blockers.csv`
- `gold_v2_17h_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED`

This means the manifest load-smoke passed. It does not mean live execution is allowed.

## Stop conditions

Stop if:

- any required artifact is missing,
- 17G status is not successful,
- mapping checks or safety matrix contain STOP,
- required manifest columns are missing,
- counts differ from expected values,
- manifest row IDs are duplicated or blank,
- source hashes are blank,
- any manifest row has live or final signal allowed,
- any external action flag is true.

## Safety

All external actions remain false:

- final signal
- Discord
- MT5
- AI API
- live hook
- NO_SIGNAL Discord notification
