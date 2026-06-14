# GOLD V3 Stage117K Spec — 107Q_JUNE_EXCLUSION_DIAGNOSIS

Created JST: `2026-06-15`

## Purpose

Stage117J showed that 107L input contains June rows, but the shadow 107Q best family output contains zero June rows.

Stage117K diagnoses why June rows disappeared:

1. Were June rows covered by 107Q target windows?
2. Were June rows removed by the selected `F002 score <= L20 T5` filter?
3. Did the selected best combo objective prefer a historical combo that does not cover June?
4. Are there non-best combos with June rows?

## Inputs

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_summary.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_selected_windows.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_window_metrics.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_trade_ledger.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117k/gold_v3_117k_june_input_rows.csv
FX_OUTPUTS/gold_v3/117k/gold_v3_117k_best_combo_june_window_diagnosis.csv
FX_OUTPUTS/gold_v3/117k/gold_v3_117k_nonbest_combo_june_diagnosis.csv
FX_OUTPUTS/gold_v3/117k/gold_v3_117k_decision.csv
FX_OUTPUTS/gold_v3/117k/gold_v3_117k_summary.json
FX_OUTPUTS/gold_v3/117k/paste_me.txt
```

## Guardrails

This stage is diagnosis-only.

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
