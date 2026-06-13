# GOLD V3 Stage107GS Spec — HIGH_WINRATE_CORE_IDENTITY_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_AUDIT_ONLY
```

## Purpose

Stage107GR confirmed the user's concern: when the portfolio is pruned for win rate, OOS win rate improves, but density falls.

Observed Stage107GR:

```text
fast_version: 107GR_FAST_V2_PRECOMPUTED_CANDIDATE_METRICS_WITH_PROGRESS_20260613
frontier_rows: 1152
best_max_oos_win_rate: 75.00%
winrate_priority_gate_count: 768
high_winrate_gate_count: 768
balanced_gate_count: 288
density_retained_gate_count: 0
```

Best split examples:

```text
TRAIN_2025_TEST_2026:
  selected_candidate_count: 1
  test_trades: 73
  test_density: 0.802/day
  test PF: 3.317
  test WR: 68.49%

TRAIN_2025H1_TEST_2025H2:
  selected_candidate_count: 2
  test_trades: 125
  test_density: 0.984/day
  test PF: 2.933
  test WR: 66.40%
```

But density-retained gate is zero, and the short recent splits have too few OOS trades.

Stage107GS identifies the actual candidate keys behind this high-win-rate core and decides whether the next stage should expand around those exact keys or redesign other vectors.

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
軽: 数秒程度
1時間を超えたら停止して報告
```

Stage107GS reads Stage107GR outputs only. It must not regenerate OHLC features or rerun M5 TP/SL outcome evaluation.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107grc/gold_v3_107gr_best_by_split.csv
FX_OUTPUTS/gold_v3/107grc/gold_v3_107gr_best_oos_trade_ledger.csv
FX_OUTPUTS/gold_v3/107grc/gold_v3_107gr_frontier_config_results.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107grc/gold_v3_107gr_winrate_density_tradeoff.csv
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gsc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gsc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gs_high_wr_core_candidate_identity.csv
gold_v3_107gs_split_core_summary.csv
gold_v3_107gs_frontier_gate_summary.csv
gold_v3_107gs_density_tradeoff_summary.csv
gold_v3_107gs_next_design_decision.csv
gold_v3_107gs_blocker_matrix.csv
gold_v3_107gs_validation_matrix.csv
gold_v3_107gs_summary.json
GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GS_HIGH_WINRATE_CORE_IDENTITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
