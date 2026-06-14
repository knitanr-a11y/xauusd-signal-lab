# GOLD V3 Stage107R5 Spec — INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_AUDIT_ONLY
```

## Why this stage exists

107R4 completed and produced a resolved ledger source contract:

```text
RESOLVED_LEDGER_SOURCE_CONTRACT_READY_FOR_PATCH_IMPLEMENTATION
```

Manual source review after 107R4 showed:

- `gold_v3_107f_no_regime_baseline_and_vol_tpsl_audit.py` preserves `exit_dt` when it reads its input ledger.
- `gold_v3_107k2_direct_regime_balanced_adaptive_score_audit.py` gets its ledger through `gold_v3_107h_train_only_feature_score_gate_audit.load_augmented_ledger()`.
- `load_augmented_ledger()` reads only the GOLD V3 input ledgers listed in `gold_v3_107gy_light_non_calendar_subfilter_search_audit.INPUTS`.
- `normalize_ledger()` preserves existing columns, but the later 107K2/107Q best ledger still lacks `exit_dt`.

Therefore the likely patch point is not arbitrary existing `exit_dt` CSV join. The likely missing contract is that the 107GO/GN/GL/GD/GB source ledgers do not emit the resolved contract columns.

## Purpose

107R5 identifies exactly which current 107H/107K2 input ledgers need a resolved-contract patch and which runtime scripts likely produce them.

This is still audit-only. It does not mutate those producer scripts.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_resolved_ledger_contract.md
```

Runtime source:

```text
scripts/gold_v3_runtime/**/*.py
```

## Inspected GOLD V3 input ledgers

From `gold_v3_107gy_light_non_calendar_subfilter_search_audit.INPUTS`:

```text
107goc/gold_v3_107go_portfolio_ledger.csv
107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
107glc/gold_v3_107gl_top_vector_trade_ledger.csv
107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

## Required resolved source contract

```text
entry_dt
exit_dt
side
result_usd
profile_id
candidate_key or global_candidate_key
family
condition
source_name
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_best_family_source_distribution.csv
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_input_ledger_contract_matrix.csv
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_producer_script_locator.csv
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_patch_target_matrix.csv
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_validation_matrix.csv
FX_OUTPUTS/gold_v3/107r5c/gold_v3_107r5_summary.json
FX_OUTPUTS/gold_v3/107r5c/GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107r5c/paste_me.txt
```

## Decisions

Allowed decisions:

```text
INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGETS_READY_FOR_107R6
INPUT_LEDGER_RESOLVED_CONTRACT_ALREADY_PRESENT_READY_FOR_107S
INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_BLOCKED_PRODUCER_NOT_LOCATED
INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_BLOCKED_INPUT_INCOMPLETE
```

## Next stage

If patch targets are found:

```text
107R6_RESOLVED_CONTRACT_OUTPUT_PATCH_AUDIT_ONLY
```

107R6 must add audit-only resolved contract output to the identified producer scripts without changing selection/scoring/runtime/live paths.

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
