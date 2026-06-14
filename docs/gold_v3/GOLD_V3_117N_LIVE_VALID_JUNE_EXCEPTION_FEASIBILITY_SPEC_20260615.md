# GOLD V3 Stage117N Spec — LIVE_VALID_JUNE_EXCEPTION_FEASIBILITY

Created JST: `2026-06-15`

## Purpose

Stage117M showed that restoring all 8 removed June rows is positive, but not auto-adopted.

Stage117N checks whether there is any **pre-trade-feature-only** exception rule that could restore the removed June rows without using `result_usd` as a selector.

This is still review-only because the exception idea was triggered after inspecting June behavior.

## Inputs

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/117l/gold_v3_117l_june_filter_detail.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_trade_ledger.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117n/gold_v3_117n_exception_rule_candidates.csv
FX_OUTPUTS/gold_v3/117n/gold_v3_117n_best_exception_review_ledger.csv
FX_OUTPUTS/gold_v3/117n/gold_v3_117n_decision.csv
FX_OUTPUTS/gold_v3/117n/gold_v3_117n_summary.json
FX_OUTPUTS/gold_v3/117n/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
shadow_only: true
no_auto_adoption: true
```
