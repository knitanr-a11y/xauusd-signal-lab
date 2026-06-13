# GOLD V3 Stage107GR Spec — WINRATE_FIRST_DENSITY_FRONTIER_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_AUDIT_ONLY
```

## Purpose

Stage107GP achieved the daily density target in full-period diagnostic mode, but the win rate was still too low for the user's target:

```text
107GP best full-period diagnostic:
  selected_candidate_count: 12
  business_day_trade_rate: 4.109
  PF: 2.119
  WR: 55.02%
```

Stage107GQ then showed that anchored OOS selection did not pass any OOS gate:

```text
splits_primary_oos_pass: 0
splits_exploratory_oos_pass: 0
```

OOS win rates were not strong enough:

```text
TRAIN_2025_TEST_2026:              test WR 52.31%, PF 1.77, density 1.79/day
TRAIN_2025H1_TEST_2025H2:          test WR 51.41%, PF 2.16, density 1.90/day
TRAIN_TO_2026_02_TEST_2026_03+:    test WR 51.90%, PF 1.29, density 2.14/day
TRAIN_TO_2026_04_TEST_2026_05_06:  test WR 38.24%, PF 1.19, density 2.27/day
```

The user clarified:

```text
107GPは勝率が悪いので件数を削って勝率を上げなければならない。
```

Stage107GR therefore builds a win-rate-first frontier. It deliberately reduces candidate count/trade density and tests whether OOS win rate improves enough.

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

Stage107GR reads existing candidate ledgers only. It must not regenerate OHLC features or rerun M5 TP/SL outcome evaluation.

## Inputs

Candidate ledgers, exact paths only:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Use files only if present. Do not scan broadly.

## Anchored splits

```text
TRAIN_2025_TEST_2026
TRAIN_2025H1_TEST_2025H2
TRAIN_TO_2026_02_TEST_2026_03_PLUS
TRAIN_TO_2026_04_TEST_2026_05_06
```

## Frontier configs

Stage107GR evaluates a grid of train-period selection constraints:

```text
min_train_wr: 0.55, 0.58, 0.60, 0.62
min_train_pf: 1.50, 1.80, 2.00, 2.30
max_train_negative_months: 0, 1, 2
density_target_business_day: 0.5, 1.0, 1.5, 2.0
max_candidates: 3, 5, 8, 12, 20, 40
```

The selector is win-rate-first:

```text
1. Filter by train WR/PF/negative-month constraints.
2. Rank candidates primarily by train WR, then PF, then stability.
3. Add candidates until the target density is reached or max_candidates is reached.
4. Apply those selected keys to the OOS test period only.
5. Deduplicate same entry timestamp by train score.
```

## OOS target tiers

Win-rate priority gate:

```text
test_win_rate >= 0.58
test_profit_factor >= 1.50
test_negative_month_count <= 3
```

High win-rate gate:

```text
test_win_rate >= 0.60
test_profit_factor >= 1.50
test_negative_month_count <= 3
```

Balanced practical gate:

```text
test_win_rate >= 0.55
test_profit_factor >= 1.80
test_business_day_trade_rate >= 1.0
test_negative_month_count <= 3
```

Density-retained gate:

```text
test_win_rate >= 0.55
test_profit_factor >= 1.80
test_business_day_trade_rate >= 2.0
test_negative_month_count <= 3
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107grc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107grc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gr_input_ledger_coverage.csv
gold_v3_107gr_frontier_config_results.csv
gold_v3_107gr_best_by_split.csv
gold_v3_107gr_best_overall_candidates.csv
gold_v3_107gr_best_oos_trade_ledger.csv
gold_v3_107gr_winrate_density_tradeoff.csv
gold_v3_107gr_quality_gate_matrix.csv
gold_v3_107gr_recommended_next_actions.csv
gold_v3_107gr_blocker_matrix.csv
gold_v3_107gr_validation_matrix.csv
gold_v3_107gr_summary.json
GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GR_WINRATE_FIRST_DENSITY_FRONTIER_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
