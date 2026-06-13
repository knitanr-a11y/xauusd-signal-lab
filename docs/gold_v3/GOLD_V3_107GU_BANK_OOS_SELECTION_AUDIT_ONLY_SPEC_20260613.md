# GOLD V3 Stage107GU Spec — BANK_OOS_SELECTION_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GU_BANK_OOS_SELECTION_AUDIT_ONLY
```

## Purpose

Stage107GT corrected the design direction to a multi-vector candidate bank:

```text
candidate_bank_rows: 6519
accepted_candidate_count: 144
LONG core_high_wr: 14
SHORT core_high_wr: 6
```

Stage107GU tests that candidate-bank approach without full-period selection leakage.

Correct operating concept:

```text
Do not enlarge one LONG/SHORT signal.
Stack multiple independent candidate vectors.
Candidate count may be 10, 50, or 100 if quality remains acceptable.
Select candidates using only train-period metrics.
Apply selected candidates to OOS period.
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
軽〜中: 数秒〜数分程度
1時間を超えたら停止して報告
```

No OHLC feature regeneration and no M5 TP/SL re-evaluation.

## Inputs

Exact candidate ledgers only, if present:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Do not scan broadly.

## Anchored splits

```text
TRAIN_2025_TEST_2026
TRAIN_2025H1_TEST_2025H2
TRAIN_TO_2026_02_TEST_2026_03_PLUS
TRAIN_TO_2026_04_TEST_2026_05_06
```

## Selection modes

For each split, build train-only candidate metrics and evaluate these bank tiers:

```text
core_high_wr:
  train WR >= 0.60, train PF >= 1.80, train trades >= 30

practical_quality:
  train WR >= 0.58, train PF >= 1.60, train trades >= 50

density_safe:
  train WR >= 0.55, train PF >= 1.50, train trades >= 80

exploratory:
  train WR >= 0.52, train PF >= 1.30, train trades >= 100
```

Each tier is stacked by top N:

```text
N = 3, 5, 10, 20, 30, 50, 100
```

Same-timestamp conflicts are de-duplicated by train score.

## OOS gates

High-win-rate gate:

```text
test WR >= 0.60
test PF >= 1.50
test trades >= 20
```

Practical bank gate:

```text
test WR >= 0.58
test PF >= 1.60
test business_day_trade_rate >= 1.0
```

Density-2 acceptable gate:

```text
test WR >= 0.55
test PF >= 1.50
test business_day_trade_rate >= 2.0
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107guc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107guc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gu_input_ledger_coverage.csv
gold_v3_107gu_train_candidate_metrics.csv
gold_v3_107gu_oos_bank_frontier.csv
gold_v3_107gu_best_by_split.csv
gold_v3_107gu_best_overall_frontier.csv
gold_v3_107gu_best_oos_trade_ledger.csv
gold_v3_107gu_selected_candidate_keys.csv
gold_v3_107gu_quality_gate_matrix.csv
gold_v3_107gu_recommended_next_actions.csv
gold_v3_107gu_blocker_matrix.csv
gold_v3_107gu_validation_matrix.csv
gold_v3_107gu_summary.json
GOLD_V3_107GU_BANK_OOS_SELECTION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GU_BANK_OOS_SELECTION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GU_BANK_OOS_SELECTION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
