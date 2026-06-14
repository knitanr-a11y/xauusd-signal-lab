# GOLD V3 Stage117J Spec — SHADOW_107Q_RERUN_AUDIT

Created JST: `2026-06-15`

## Purpose

Stage117I showed that the 107Q generator inputs can support a rerun through early June:

```text
107L max entry_dt: 2026-06-05 15:15:00
107L June rows: 8
107M frontier rows: 571
```

Stage117J reruns the 107Q stable filter family replay logic in shadow mode and writes only to:

```text
FX_OUTPUTS/gold_v3/117j
```

It does not overwrite `107qc`, `107r6c`, or `109c`.

## Inputs

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_family_sweep_summary.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_all_selected_thresholds.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_all_window_metrics.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/117j/gold_v3_117j_shadow_107q_best_family_regime_metrics.csv
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
