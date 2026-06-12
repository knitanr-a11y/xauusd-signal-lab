# GOLD V3 Stage107GJ Spec — ANCHORED_TRAIN_TEST_SELECTION_STABILITY_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_AUDIT_ONLY
```

## Purpose

Stage107GI found a practical sticky gate frontier:

```text
candidate_monthly_gate
lookback: 3
min_train_trades: 20
min_train_pf: 1.8
min_train_wr: 0.5
max_train_negative_months: 0
trades: 305
win_rate: 69.51%
PF: 3.50
negative_month_count: 0
quality gates: PASS 4
```

However, the candidate universe still comes from prior full-period candidate generation.

Stage107GJ performs an anchored train/test selection audit using the existing primitive-combo candidate universe:

```text
For each train/test split:
  1. Use only train-period candidate results to select candidates.
  2. Apply selected candidates to the test period.
  3. Resolve same-entry conflicts by train score.
  4. Report out-of-sample test performance.
```

This does not yet regenerate the entire candidate universe from OHLC inside train only. It is a necessary intermediate bias check before a heavier train-only OHLC universe generation stage.

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
軽〜中: 数分〜20分程度
1時間を超えたら停止して報告
```

This stage reads existing Stage107GB candidate ledger and does not generate OHLC features.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Optional reference:

```text
FX_OUTPUTS/gold_v3/107gic/gold_v3_107gi_practical_recommendation.csv
```

## Anchored splits

```text
TRAIN_2025_TEST_2026
TRAIN_2025H1_TEST_2025H2
TRAIN_TO_2026_02_TEST_2026_03_PLUS
TRAIN_TO_2026_04_TEST_2026_05_06
```

Splits with insufficient train or test trades are reported but not used for final recommendation.

## Selection grid

```text
min_train_trades: 20, 40, 80
min_train_pf: 1.50, 1.80, 2.00
min_train_wr: 0.50, 0.55, 0.60
max_train_negative_months: 0, 1, 2
max_candidates_per_side: 1, 2, 3
max_overlap: 0.35
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gjc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gjc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gj_split_config_summary.csv
gold_v3_107gj_best_by_split.csv
gold_v3_107gj_selected_candidate_log.csv
gold_v3_107gj_best_selected_trade_ledger.csv
gold_v3_107gj_stability_summary.csv
gold_v3_107gj_quality_gate_matrix.csv
gold_v3_107gj_limitations.csv
gold_v3_107gj_recommended_next_actions.csv
gold_v3_107gj_blocker_matrix.csv
gold_v3_107gj_validation_matrix.csv
gold_v3_107gj_summary.json
GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GJ_ANCHORED_TRAIN_TEST_SELECTION_STABILITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
