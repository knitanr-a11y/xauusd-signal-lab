# GOLD V3 Stage107GI Spec — STICKY_GATE_VOLUME_QUALITY_FRONTIER_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_AUDIT_ONLY
```

## Purpose

Stage107GH found a high-quality sticky gate:

```text
candidate_monthly_gate
trades: 155
win_rate: 72.26%
PF: 3.88
negative_month_count: 0
```

But it reduced trade count too much compared with the fixed baseline:

```text
fixed baseline trades: 518
win_rate: 65.44%
PF: 3.02
negative_month_count: 0
```

Stage107GI compares the volume/quality frontier instead of selecting only the highest PF configuration.

It answers:

```text
1. What is the best config if trades >= 150?
2. What is the best config if trades >= 250?
3. What is the best config if trades >= 300?
4. What is the best config if trades >= 400?
5. Which config is the best practical trade-off?
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

This stage reads Stage107GH summary tables only. It must not run OHLC feature generation or candidate search.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107ghc/gold_v3_107gh_gate_config_summary.csv
FX_OUTPUTS/gold_v3/107ghc/gold_v3_107gh_best_gate_selected_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
```

## Frontier tiers

```text
min_trades: 100, 150, 250, 300, 400, 500
```

Score each tier with:

```text
PF quality
win rate quality
negative month penalty
sum result
trade count sanity
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gic/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gic/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gi_volume_quality_frontier.csv
gold_v3_107gi_top_configs_by_tier.csv
gold_v3_107gi_practical_recommendation.csv
gold_v3_107gi_quality_gate_matrix.csv
gold_v3_107gi_limitations.csv
gold_v3_107gi_recommended_next_actions.csv
gold_v3_107gi_blocker_matrix.csv
gold_v3_107gi_validation_matrix.csv
gold_v3_107gi_summary.json
GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GI_STICKY_GATE_VOLUME_QUALITY_FRONTIER_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
