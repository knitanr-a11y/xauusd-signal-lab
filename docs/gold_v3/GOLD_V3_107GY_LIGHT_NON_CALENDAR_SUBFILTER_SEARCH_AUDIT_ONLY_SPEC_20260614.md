# GOLD V3 Stage107GY-A Spec — LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_AUDIT_ONLY
```

## Purpose

Stage107GX produced percent progress, but it was heavy and took about 9.5 hours. It found tiny 65%+ OOS pockets, but not enough OOS trades:

```text
elapsed_seconds: 34185.15
primary_65_gate_count: 0
high_volume_65_gate_count: 0
best_wr: 100%
best_trades: 5
```

Stage107GY-A is a lighter diagnostic stage. It does not try a huge combinatorial grid. Instead, it tests a small set of entry-time, live-knowable non-calendar features to discover which dimensions can lift OOS win rate toward 65% while preserving enough trades.

The user clarified:

```text
勝率65%以上がほしい。
勝率が高ければ日に何十回でもよい。
今日は終日作業できるが軽量化が望ましい。
必要なら重くなってもよい。
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

## Live-knowable feature policy

Allowed features must be computable at or before `entry_dt` from already closed CSV rows only.

Allowed examples:

```text
M15 ATR14/ATR28
M15 RSI14
M15 EMA20/EMA50/EMA100 relation
M15 distance from EMA normalized by ATR
M15 candle body/range normalized by ATR
H1/H4/D1 EMA trend as-of entry
H1/H4 RSI as-of entry
H1/H4 ATR state as-of entry
multi-timeframe trend alignment as-of entry
```

Forbidden:

```text
future TP/SL
exit result
future high/low/close
future ATR/H4/D1 state
unresolved future horizon
open/incomplete candles
```

## Inputs

Prior candidate-bank outputs:

```text
FX_OUTPUTS/gold_v3/107gvc/gold_v3_107gv_density2_pass_configs.csv
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
```

Exact candidate ledgers, if present:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Exact OHLC CSVs, if present:

```text
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
gold#_m15.csv
gold#_h1.csv
gold#_h4.csv
gold#_d1.csv
```

Do not scan broadly.

## Runtime and progress

Expected runtime:

```text
light-to-medium; target minutes to under 1 hour
```

Progress must be printed as:

```text
progress 37.5% complete / 62.5% remaining | step x/y | ...
```

## Method

1. Load candidate bank ledgers.
2. Load exact M15/H1/H4/D1 OHLC files.
3. Compute live-knowable features using only closed rows.
4. As-of join features to candidate trade entries.
5. Select top Stage107GV density2 configs.
6. For each selected base candidate, test a small number of feature filters.
7. Select train-only high-WR/high-PF subfilters.
8. Stack selected subfilters.
9. Evaluate OOS by anchored split.

## OOS gates

Primary target:

```text
OOS WR >= 0.65
OOS PF >= 1.50
OOS trades >= 30
```

High-volume target:

```text
OOS WR >= 0.65
OOS PF >= 1.50
OOS business-day trade rate >= 2.0
```

Review target:

```text
OOS WR >= 0.62
OOS PF >= 1.80
OOS trades >= 50
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107gyc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gyc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gy_ohlc_coverage.csv
gold_v3_107gy_input_ledger_coverage.csv
gold_v3_107gy_feature_join_coverage.csv
gold_v3_107gy_subfilter_metrics.csv
gold_v3_107gy_stack_frontier.csv
gold_v3_107gy_best_stack_ledger.csv
gold_v3_107gy_selected_subfilters.csv
gold_v3_107gy_quality_gate_matrix.csv
gold_v3_107gy_next_action_decision.csv
gold_v3_107gy_blocker_matrix.csv
gold_v3_107gy_validation_matrix.csv
gold_v3_107gy_summary.json
GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
