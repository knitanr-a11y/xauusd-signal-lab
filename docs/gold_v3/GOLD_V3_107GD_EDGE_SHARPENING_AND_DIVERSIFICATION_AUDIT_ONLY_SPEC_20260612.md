# GOLD V3 Stage107GD Spec — EDGE_SHARPENING_AND_DIVERSIFICATION_AUDIT_ONLY

Created JST: `2026-06-12`

Stage:

```text
GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_AUDIT_ONLY
```

## Purpose

Stage107GD follows the user's direction:

```text
件数を削って勝率を上げる
少ないなら別のベクトルのロング・ショートを増やす
```

Stage107GC found balanced candidates:

```text
LONG: h4_up&h1_up&pullback_long, trades 290, WR 68.28%, PF 3.24
SHORT: h1_down&pullback_short&session_7_15, trades 145, WR 62.76%, PF 2.69
```

Stage107GD must explore two paths:

```text
A. Sharpening: add filters or choose stricter descendants to improve win-rate/PF while accepting fewer trades.
B. Diversification: add non-overlapping edge vectors to increase total trades without diluting PF too much.
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

Primary Stage107GC/107GB outputs:

```text
FX_OUTPUTS/gold_v3/107gcc/gold_v3_107gc_quality_rebalanced_candidates.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_split_summary.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_monthly_summary.csv
```

## Required analysis

### Sharpening matrix

Compare parent/child condition relationships:

```text
parent: h4_up&h1_up
child:  h4_up&h1_up&pullback_long
```

Report:

```text
trade_reduction_ratio
win_rate_delta
pf_delta
negative_month_delta
sharpening_score
```

### Diversified portfolio matrix

Build side-specific portfolios using candidates that satisfy quality thresholds and have low overlap.

Default quality thresholds:

```text
min_trades: 80
min_profit_factor: 1.80
min_win_rate: 0.55
max_negative_month_count: 2
max_overlap_with_selected: 0.35
max_candidates_per_side: 6
```

Report:

```text
portfolio_side
candidate_count
union_trades
win_rate
profit_factor
sum_result_usd
negative_month_count
overlap_summary
```

### Conflict audit

If both LONG and SHORT portfolios exist, report same-entry conflicts across portfolio union.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gdc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gdc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gd_sharpening_matrix.csv
gold_v3_107gd_diversified_candidate_selection.csv
gold_v3_107gd_diversified_portfolio_summary.csv
gold_v3_107gd_diversified_portfolio_ledger.csv
gold_v3_107gd_long_short_portfolio_conflict.csv
gold_v3_107gd_recommended_next_actions.csv
gold_v3_107gd_blocker_matrix.csv
gold_v3_107gd_validation_matrix.csv
gold_v3_107gd_summary.json
GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
