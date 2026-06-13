# GOLD V3 Stage107GM Spec — NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_AUDIT_ONLY
```

## Purpose

Stage107GL successfully generated new LONG/SHORT vector families, but its default best-score output was too influenced by trade count and total profit.

Observed Stage107GL best candidates:

```text
best_new_long_vector:
  trades: 6578
  win_rate: 40.26%
  PF: 1.57
  negative_month_count: 5
  2026 PF: 0.97

best_new_short_vector:
  trades: 849
  win_rate: 43.23%
  PF: 1.52
  2025 trades: 0
  2026-only exposure
```

Stage107GM re-ranks the 107GL candidate table using quality and split stability, not raw total profit.

It answers:

```text
1. Are there any new LONG vectors with enough trades and quality?
2. Are there any new SHORT vectors with enough trades and quality?
3. Are candidates stable across 2025 and 2026, or only period-specific?
4. Which candidates are rejected and why?
5. Should we proceed to anchored train/test on new vectors or redesign vector families again?
```

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

Expected runtime:

```text
軽: 数秒〜数分程度
1時間を超えたら停止して報告
```

This stage reads Stage107GL summary CSVs only. It must not re-run OHLC feature generation or M5 TP/SL evaluation.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_vector_candidate_summary.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_side_family_summary.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_anchored_split_summary.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
```

## Quality tiers

Strict viable:

```text
trades >= 150
PF >= 2.00
WR >= 0.55
negative_month_count <= 2
```

Practical viable:

```text
trades >= 250
PF >= 1.80
WR >= 0.50
negative_month_count <= 2
```

Exploratory gap-fill:

```text
trades >= 80
PF >= 1.60
WR >= 0.48
negative_month_count <= 3
```

Split stability flags:

```text
2025_coverage_required: 2025_trades >= 20
2026_coverage_required: 2026_trades >= 20
2026_not_broken: 2026_profit_factor >= 1.20 if 2026_trades >= 20
2025H2_not_broken: 2025H2_profit_factor >= 1.20 if 2025H2_trades >= 20
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gmc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gmc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gm_quality_rebalanced_candidates.csv
gold_v3_107gm_viable_candidate_frontier.csv
gold_v3_107gm_rejected_candidates.csv
gold_v3_107gm_family_quality_summary.csv
gold_v3_107gm_side_gap_summary.csv
gold_v3_107gm_quality_gate_matrix.csv
gold_v3_107gm_recommended_next_actions.csv
gold_v3_107gm_blocker_matrix.csv
gold_v3_107gm_validation_matrix.csv
gold_v3_107gm_summary.json
GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GM_NEW_VECTOR_QUALITY_REBALANCE_AND_SPLIT_FRONTIER_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
