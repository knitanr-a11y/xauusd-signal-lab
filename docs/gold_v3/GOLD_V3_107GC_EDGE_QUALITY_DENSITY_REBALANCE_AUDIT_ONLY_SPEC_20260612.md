# GOLD V3 Stage107GC Spec — EDGE_QUALITY_DENSITY_REBALANCE_AUDIT_ONLY

Created JST: `2026-06-12`

Stage:

```text
GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_AUDIT_ONLY
```

## Purpose

Stage107GB proved that the data covers 2025-01-02 through 2026-06-12 and that the low trade count in 107G was partly due to strict candidate ranking/cooldown.

However, Stage107GB's top LONG candidate was too broad:

```text
LONG h4_up&h1_up
trades: 7818
win_rate: 39.78%
PF: 1.57
```

This is not an ideal edge condition even if total profit is high. Stage107GC re-scores 107GB candidates to prioritize:

```text
PF quality
win-rate quality
monthly stability
2025/2026 split stability
density sanity
not too broad, not too rare
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

## Inputs

Primary Stage107GB outputs:

```text
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_density_summary.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_split_summary.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_monthly_summary.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_feature_coverage.csv
```

## Rebalance rules

Stage107GC must report at least:

```text
trades_per_month
raw_events_per_month
broadness_flag
rarity_flag
quality_score
stability_score
balanced_score
```

Default density sanity thresholds:

```text
minimum trades: 80
minimum trades per month: 4
maximum trades per month: 250
broadness flag: trades per month > 250 or raw_events per month > 400
rarity flag: trades per month < 4
```

A candidate should be penalized if:

```text
win_rate < 0.45
profit_factor < 1.50
negative_month_count > 3
2025 PF < 1.10 when 2025 trades exist
2026 PF < 1.10 when 2026 trades exist
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gcc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gcc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gc_quality_rebalanced_candidates.csv
gold_v3_107gc_rejected_or_penalized_candidates.csv
gold_v3_107gc_best_by_side.csv
gold_v3_107gc_recommended_next_test_matrix.csv
gold_v3_107gc_blocker_matrix.csv
gold_v3_107gc_validation_matrix.csv
gold_v3_107gc_summary.json
GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GC_EDGE_QUALITY_DENSITY_REBALANCE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
