# GOLD V3 Stage117I Spec — 107Q_GENERATOR_INPUT_FEASIBILITY_AUDIT

Created JST: `2026-06-15`

## Purpose

Stage117H showed that `107qc/gold_v3_107q_best_family_trade_ledger.csv` stops before June.

The 107Q generator reads:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
```

Stage117I checks whether those inputs can support a 107Q rerun through June.

## Outputs

```text
FX_OUTPUTS/gold_v3/117i/gold_v3_117i_107q_input_coverage.csv
FX_OUTPUTS/gold_v3/117i/gold_v3_117i_107l_monthly_metrics.csv
FX_OUTPUTS/gold_v3/117i/gold_v3_117i_107m_frontier_inventory.csv
FX_OUTPUTS/gold_v3/117i/gold_v3_117i_decision.csv
FX_OUTPUTS/gold_v3/117i/gold_v3_117i_summary.json
FX_OUTPUTS/gold_v3/117i/paste_me.txt
```

## Guardrails

This stage does not regenerate 107Q and does not overwrite any source output.

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
