# GOLD V3 Stage107GT Spec — MULTI_VECTOR_CANDIDATE_BANK_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_AUDIT_ONLY
```

## Purpose

The user clarified that the target is not to increase trade count from one LONG/SHORT signal.

Correct interpretation:

```text
今まで出た複数の候補・別ベクトルを候補バンクとして扱う。
候補数は10個でも100個でもよい。
各候補は別々の条件・別々のvectorとして残す。
LONG/SHORT合算で必要な取引密度を作る。
ただし勝率が悪い候補を足して密度だけ上げるのは不可。
```

Stage107GS incorrectly suggested expanding around a single high-win-rate core. Stage107GT corrects the direction by auditing all previously produced candidate ledgers as a multi-vector bank.

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

## Method

1. Normalize every ledger row to a `global_candidate_key`.
2. Treat each key as a separate candidate vector.
3. Compute full-period, year, and anchored split OOS metrics per candidate.
4. Build candidate-bank tiers:

```text
core_high_wr:      WR >= 0.60 and PF >= 1.80 and trades >= 30
practical_quality: WR >= 0.58 and PF >= 1.60 and trades >= 50
density_safe:      WR >= 0.55 and PF >= 1.50 and trades >= 80
exploratory:       WR >= 0.52 and PF >= 1.30 and trades >= 100
```

5. Build portfolio frontiers using top N candidates:

```text
N = 3, 5, 10, 20, 30, 50, 100
```

6. Report whether candidate-bank style can achieve both quality and density without relying on a single signal.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gtc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gtc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gt_input_ledger_coverage.csv
gold_v3_107gt_candidate_bank_metrics.csv
gold_v3_107gt_candidate_bank_tiers.csv
gold_v3_107gt_top_candidate_bank.csv
gold_v3_107gt_portfolio_size_frontier.csv
gold_v3_107gt_best_bank_portfolio_ledger.csv
gold_v3_107gt_source_side_summary.csv
gold_v3_107gt_next_action_decision.csv
gold_v3_107gt_blocker_matrix.csv
gold_v3_107gt_validation_matrix.csv
gold_v3_107gt_summary.json
GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GT_MULTI_VECTOR_CANDIDATE_BANK_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
