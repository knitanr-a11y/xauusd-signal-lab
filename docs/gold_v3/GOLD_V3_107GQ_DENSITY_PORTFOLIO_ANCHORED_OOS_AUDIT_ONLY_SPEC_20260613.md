# GOLD V3 Stage107GQ Spec — DENSITY_PORTFOLIO_ANCHORED_OOS_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_AUDIT_ONLY
```

## Purpose

The user clarified that the number of vector candidates is not a problem:

```text
候補が10個でも100個でもよい。
LONG/SHORT合算で1日2回以上のトレード密度があればよい。
```

Stage107GP found a density-satisfying diagnostic portfolio:

```text
portfolio_mode: quality_candidates_only
selected_candidate_count: 12
trades: 1545
business_day_trade_rate: 4.109
PF: 2.119
WR: 55.02%
negative_month_count: 0
primary_density_quality_gate: PASS
```

Stage107GQ tests whether a density-target portfolio can be selected using only prior training-period results and then applied out-of-sample.

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

Stage107GQ reads existing candidate ledgers only. It must not regenerate OHLC features or rerun M5 TP/SL outcome evaluation.

## Inputs

Candidate ledgers, exact paths only:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Reference input:

```text
FX_OUTPUTS/gold_v3/107gpc/gold_v3_107gp_selected_candidates.csv
FX_OUTPUTS/gold_v3/107gpc/gold_v3_107gp_best_density_portfolio_ledger.csv
```

Use files only if present. Do not scan broadly.

## Anchored splits

```text
TRAIN_2025_TEST_2026
TRAIN_2025H1_TEST_2025H2
TRAIN_TO_2026_02_TEST_2026_03_PLUS
TRAIN_TO_2026_04_TEST_2026_05_06
```

## Selection rule

For each split:

1. Build candidate metrics using only train-period rows.
2. Select candidates greedily by train density-quality score.
3. Stop when train business-day density reaches at least 2.0, or when max candidates is reached.
4. Apply selected candidate keys to the test period only.
5. Deduplicate same entry timestamp by train score.
6. Compute test density and quality.

Candidate count is not capped tightly. Default max candidates:

```text
max_candidates: 100
```

## OOS gates

Primary OOS gate:

```text
test_business_day_trade_rate >= 2.0
test_profit_factor >= 1.80
test_win_rate >= 0.50
test_negative_month_count <= 3
```

Exploratory OOS gate:

```text
test_business_day_trade_rate >= 2.0
test_profit_factor >= 1.50
test_win_rate >= 0.45
test_negative_month_count <= 4
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gqc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gqc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gq_input_ledger_coverage.csv
gold_v3_107gq_split_selection_log.csv
gold_v3_107gq_split_oos_summary.csv
gold_v3_107gq_oos_trade_ledger.csv
gold_v3_107gq_fixed_107gp_selected_benchmark.csv
gold_v3_107gq_quality_gate_matrix.csv
gold_v3_107gq_recommended_next_actions.csv
gold_v3_107gq_blocker_matrix.csv
gold_v3_107gq_validation_matrix.csv
gold_v3_107gq_summary.json
GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GQ_DENSITY_PORTFOLIO_ANCHORED_OOS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
