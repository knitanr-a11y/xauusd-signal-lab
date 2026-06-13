# GOLD V3 Stage107GO Spec — ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_AUDIT_ONLY
```

## Purpose

Stage107GN found one high-quality but very small LONG atomic seed and no viable SHORT seed:

```text
best_atomic_long:
  trades: 31
  win_rate: 61.29%
  PF: 3.17
  2025 PF: 3.00
  2026 PF: 4.00

good_counts:
  LONG=0
  SHORT=0
```

The issue is no longer simply whether one standalone atomic candidate passes. Stage107GO checks whether the available atomic candidates can be combined into a diversified portfolio without rerunning M5 TP/SL evaluation.

It answers:

```text
1. Can multiple small LONG atomic candidates be bundled to reach practical trade count?
2. Does the bundled LONG portfolio retain PF/WR quality?
3. Can SHORT improve through bundling, or is SHORT still a design gap?
4. Which side should be redesigned next?
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

Stage107GO reads Stage107GN summary and top ledger only. It must not regenerate OHLC features or rerun M5 TP/SL outcome evaluation.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_candidate_summary.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_long_candidates.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_short_candidates.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_family_summary.csv
```

## Method

1. Rebuild candidate keys:

```text
side||family||condition||profile_id||CD{cooldown_bars}
```

2. Score candidate quality from actual ledger rows where available.
3. Greedy-select diversified portfolios by side.
4. Deduplicate same-side same-entry candidates by quality score.
5. Resolve long/short conflicts only in a separate combined diagnostic; do not alter source candidate pool.
6. Report whether each side has a viable portfolio.

## Portfolio viability gates

LONG portfolio practical gate:

```text
trades >= 100
PF >= 2.00
WR >= 0.55
negative_month_count <= 2
```

SHORT portfolio practical gate:

```text
trades >= 100
PF >= 1.80
WR >= 0.50
negative_month_count <= 2
```

The SHORT threshold is slightly lower because Stage107GK/107GN showed SHORT is the weaker side and may require redesign even if a weak exploratory basket appears.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107goc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107goc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107go_candidate_ledger_metrics.csv
gold_v3_107go_diversified_selection.csv
gold_v3_107go_portfolio_ledger.csv
gold_v3_107go_side_portfolio_summary.csv
gold_v3_107go_combined_conflict_summary.csv
gold_v3_107go_side_gap_decision.csv
gold_v3_107go_quality_gate_matrix.csv
gold_v3_107go_recommended_next_actions.csv
gold_v3_107go_blocker_matrix.csv
gold_v3_107go_validation_matrix.csv
gold_v3_107go_summary.json
GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
