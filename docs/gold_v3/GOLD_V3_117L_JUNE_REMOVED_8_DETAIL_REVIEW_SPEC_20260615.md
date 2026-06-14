# GOLD V3 Stage117L Spec — JUNE_REMOVED_8_DETAIL_REVIEW

Created JST: `2026-06-15`

## Purpose

Stage117J showed that 107L input has 8 June rows, but shadow 107Q best output has 0 June rows.

Stage117L extracts those 8 June rows from 107L and evaluates them against the Stage117J selected F002 `score <=` threshold.

## Inputs

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_selected_windows.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_trade_ledger.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117l/gold_v3_117l_june_107l_rows.csv
FX_OUTPUTS/gold_v3/117l/gold_v3_117l_june_filter_detail.csv
FX_OUTPUTS/gold_v3/117l/gold_v3_117l_decision.csv
FX_OUTPUTS/gold_v3/117l/gold_v3_117l_summary.json
FX_OUTPUTS/gold_v3/117l/paste_me.txt
```

## Guardrails

Diagnosis-only. No source output is overwritten.

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
