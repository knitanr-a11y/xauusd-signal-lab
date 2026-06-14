# GOLD V3 Stage117M Spec — JUNE_RESTORE_POLICY_COMPARISON

Created JST: `2026-06-15`

## Purpose

Compare review-only policies for the 8 June rows that Stage117L proved were all removed by the F002 `score <= threshold` filter.

This stage does not approve live use. It only compares outcomes.

## Policies

```text
KEEP_F002_EXCLUSION
RESTORE_ALL_8_JUNE_REVIEW_ONLY
RESTORE_WINNERS_ONLY_POSTHOC_INVALID_REFERENCE_ONLY
```

The winners-only policy is explicitly invalid for live trading because it uses known outcomes. It is included only as an upper-bound sanity check.

## Inputs

```text
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/117l/gold_v3_117l_june_filter_detail.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117m/gold_v3_117m_policy_comparison.csv
FX_OUTPUTS/gold_v3/117m/gold_v3_117m_restore_all_8_review_ledger.csv
FX_OUTPUTS/gold_v3/117m/gold_v3_117m_decision.csv
FX_OUTPUTS/gold_v3/117m/gold_v3_117m_summary.json
FX_OUTPUTS/gold_v3/117m/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
shadow_only: true
```
