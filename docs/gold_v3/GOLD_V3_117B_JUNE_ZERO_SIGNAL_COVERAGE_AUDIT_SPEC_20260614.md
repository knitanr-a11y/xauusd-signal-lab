# GOLD V3 Stage117B Spec — JUNE_ZERO_SIGNAL_COVERAGE_AUDIT

Created JST: `2026-06-14`

## Purpose

Stage117A showed strong May performance, but no June selected rows appeared in the May-June validation window.

Stage117B checks whether June zero selected signals are caused by:

```text
1. normal selected-policy no-signal condition
2. selected ledger date coverage ending before June
3. M15 OHLC coverage missing June
4. mismatch between selected ledger coverage and OHLC coverage
```

## Inputs

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/112c/gold_v3_112_selected_policy_freeze_manifest.json
goldsharp_m15.csv
gold#_m15.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117b/gold_v3_117b_selected_ledger_month_counts.csv
FX_OUTPUTS/gold_v3/117b/gold_v3_117b_m15_ohlc_coverage.csv
FX_OUTPUTS/gold_v3/117b/gold_v3_117b_coverage_decision.csv
FX_OUTPUTS/gold_v3/117b/gold_v3_117b_summary.json
FX_OUTPUTS/gold_v3/117b/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```

This is coverage audit only. It does not reconstruct missing candidate logic.
