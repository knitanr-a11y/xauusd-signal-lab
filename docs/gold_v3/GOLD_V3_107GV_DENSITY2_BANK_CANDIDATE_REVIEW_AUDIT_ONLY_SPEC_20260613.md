# GOLD V3 Stage107GV Spec — DENSITY2_BANK_CANDIDATE_REVIEW_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_AUDIT_ONLY
```

## Purpose

Stage107GU confirmed that train-only multi-vector candidate-bank selection can produce OOS portfolios that pass the density-2 gate:

```text
frontier_rows: 112
high_wr_gate_count: 15
practical_bank_gate_count: 26
density2_gate_count: 32
best_max_oos_wr: 0.75
best_max_density: 18.7424
```

Stage107GV reviews only the `density2_gate=True` bank configurations and expands their candidate composition.

Correct interpretation:

```text
density2_gate is a multi-candidate portfolio result.
It is not a single signal achieving two trades per day.
```

The goal is to identify which stacked candidate-bank configuration should be inspected next.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as trading sources.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Runtime estimate

```text
軽: 数秒〜数分程度
1時間を超えたら停止して報告
```

No OHLC regeneration. No M5 TP/SL re-evaluation.

## Inputs

Required Stage107GU outputs:

```text
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_oos_bank_frontier.csv
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_train_candidate_metrics.csv
```

Exact candidate ledgers, if present, for candidate-level OOS contribution review:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Do not scan broadly.

## Review focus

For each `density2_gate=True` config:

```text
split
tier
top_n
selected_candidate_count
LONG/SHORT candidate count
OOS trades
OOS WR
OOS PF
OOS business-day rate
negative months
candidate-level train metrics
candidate-level OOS metrics
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107gvc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gvc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gv_density2_pass_configs.csv
gold_v3_107gv_density2_candidate_composition.csv
gold_v3_107gv_best_density2_config.csv
gold_v3_107gv_best_density2_candidate_detail.csv
gold_v3_107gv_side_mix_summary.csv
gold_v3_107gv_next_action_decision.csv
gold_v3_107gv_blocker_matrix.csv
gold_v3_107gv_validation_matrix.csv
gold_v3_107gv_summary.json
GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GV_DENSITY2_BANK_CANDIDATE_REVIEW_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
