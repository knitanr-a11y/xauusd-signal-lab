# GOLD V3 Stage117J Spec — SHADOW_107Q_RERUN_FROM_107L_JUNE_INPUT

Created JST: `2026-06-15`

## Purpose

Stage117I proved that the 107Q generator inputs are present and 107L has June rows:

```text
107L max_entry_dt: 2026-06-05 15:15:00
107L june_rows: 8
107M rows: 571
```

Stage117J reruns the 107Q stable filter family replay into a shadow output directory:

```text
FX_OUTPUTS/gold_v3/117j
```

It must not overwrite:

```text
FX_OUTPUTS/gold_v3/107qc
FX_OUTPUTS/gold_v3/107r6c
FX_OUTPUTS/gold_v3/109c
```

## Inputs

Same as Stage107Q:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_summary.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_monthly_metrics.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_decision.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_summary.json
FX_OUTPUTS/gold_v3/117j/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
shadow_only: true
```
