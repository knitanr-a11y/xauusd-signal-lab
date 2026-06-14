# GOLD V3 Stage117A Spec — MAY_JUNE_SELECTED_SIGNAL_VALIDATION

Created JST: `2026-06-14`

## Purpose

Stage117A validates the selected GOLD V3 signal ledger for May and June 2026.

This stage answers whether the selected signals have already been reviewed specifically for:

```text
2026-05-01 <= entry_dt < 2026-07-01
```

## Input

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/112c/gold_v3_112_selected_policy_freeze_manifest.json
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_may_june_trade_ledger.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_monthly_metrics.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_side_month_metrics.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_daily_metrics.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_profile_metrics.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_candidate_metrics_top.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_validation_matrix.csv
FX_OUTPUTS/gold_v3/117a/gold_v3_117a_summary.json
FX_OUTPUTS/gold_v3/117a/paste_me.txt
```

## Guardrails

This is audit-only historical validation.

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
mt5_order_execution: false
```

Stage117A does not create live orders and does not reconstruct missing candidate logic.
