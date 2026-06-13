# GOLD V3 Stage107GP Spec — DAILY_DENSITY_TARGET_PORTFOLIO_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_AUDIT_ONLY
```

## Purpose

The user clarified the operational density target:

```text
LONG and SHORT from all separate vector candidates combined should average at least 2 trades per day.
```

Stage107GO showed:

```text
LONG portfolio:
  trades: 115
  win_rate: 59.13%
  PF: 2.89
  negative_month_count: 2
  practical gate: PASS

SHORT portfolio:
  trades: 70
  win_rate: 42.86%
  PF: 1.50
  practical gate: FAIL

Combined portfolio rows: 185
```

The quality is promising on LONG, but total density is not enough.

Stage107GP evaluates portfolio density explicitly and answers:

```text
1. What is the current trades-per-business-day density?
2. Can existing candidate ledgers be combined to reach >= 2 trades per business day?
3. If density is reached, what PF/WR degradation occurs?
4. Which side is the bottleneck: LONG density, SHORT quality, or both?
5. Should the next step prioritize density expansion, SHORT redesign, or TP/SL/timeframe redesign?
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

Stage107GP reads existing candidate ledgers only. It must not regenerate OHLC features or rerun M5 TP/SL outcome evaluation.

## Inputs

Primary required input:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
```

Optional candidate-ledger inputs:

```text
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Use optional ledgers only if present. Do not scan broadly.

## Density target

Primary density metric:

```text
business_day_trade_rate = total_trades / business_days_between_min_and_max_entry_date
```

Target:

```text
business_day_trade_rate >= 2.0
```

Also report:

```text
calendar_day_trade_rate
active_trade_day_rate
```

## Portfolio build modes

Stage107GP creates diagnostic portfolios:

```text
atomic_current_107GO
quality_candidates_only
balanced_density_expansion
density_target_relaxed
all_available_diagnostic
```

These are audit-only diagnostic portfolios, not live candidate approval.

## Quality gates

Primary practical density gate:

```text
business_day_trade_rate >= 2.0
combined PF >= 1.80
combined WR >= 0.50
negative_month_count <= 3
```

Exploratory density gate:

```text
business_day_trade_rate >= 2.0
combined PF >= 1.50
combined WR >= 0.45
negative_month_count <= 4
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gpc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gpc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gp_input_ledger_coverage.csv
gold_v3_107gp_candidate_metrics.csv
gold_v3_107gp_portfolio_density_summary.csv
gold_v3_107gp_best_density_portfolio_ledger.csv
gold_v3_107gp_selected_candidates.csv
gold_v3_107gp_side_density_summary.csv
gold_v3_107gp_density_gap_decision.csv
gold_v3_107gp_quality_gate_matrix.csv
gold_v3_107gp_recommended_next_actions.csv
gold_v3_107gp_blocker_matrix.csv
gold_v3_107gp_validation_matrix.csv
gold_v3_107gp_summary.json
GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GP_DAILY_DENSITY_TARGET_PORTFOLIO_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
