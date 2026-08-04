# BTC AI V1 — シンプルルール意味的組み合わせ研究 正式結果

日付: 2026-08-04  
branch: `feature/btc-simple-rule-combination-research`  
事前登録commit: `b8357380c4e23ee1b325a7ab0caf2ba9a792e56e`

## 正式結論

`BTC_AI_V1_SIMPLE_RULE_SEMANTIC_COMBINATIONS_ALL_FOUR_REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE`

4つの組み合わせはすべて事前登録gate不合格。新しいProspective Shadowは作成しない。Stage55は変更していない。

## 研究境界

- prior cycleの良かった方向・月・volatility帯はselectionに使用しない
- 4 combination family、各1 configurationのみ
- MLなし
- sourceはcausal candidate ledgerのformal base時刻・方向・ATRだけ
- prior trade outcome ledger、exit、PnLは組み合わせ候補作成に不使用
- closed OHLC、exact M1、fallbackなし、same-M1 collisionはSL優先
- 全family共通: M15 ATR14 × 1.00 SL、2R TP、360 existing M1 hold、cost 22.50 USD

## pipeline件数

| family | raw | dedup | exact M1 | one-position | resolved-only | 抑制 |
|---|---:|---:|---:|---:|---:|---:|
| H1 trend × compression retest | 515 | 515 | 515 | 485 | 485 | 30 |
| H1 trend × previous D1 sweep | 10 | 10 | 10 | 10 | 10 | 0 |
| previous D1 sweep × ATR exhaustion | 103 | 103 | 103 | 100 | 100 | 3 |
| pullback → compression retest | 281 | 281 | 281 | 267 | 267 | 14 |

health gateは全familyでOFF / not applicable。未解決tradeは0件。

## Formal period 2024～2026年7月

| family | trades | 勝率 | PF | net USD | Max DD | マイナス月 / 31 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---|
| H1 trend × compression retest | 344 | 32.56% | 0.857 | -8,532.20 | 11,878.27 | 21 | REJECT |
| H1 trend × previous D1 sweep | 3 | 0.00% | 0.000 | -2,003.13 | 2,003.13 | 3 | REJECT |
| previous D1 sweep × ATR exhaustion | 75 | 33.33% | 0.820 | -3,431.94 | 6,434.53 | 18 | REJECT |
| pullback → compression retest | 188 | 35.11% | 0.924 | -2,370.47 | 4,843.24 | 19 | REJECT |

## 年・期間別

### H1 trend × compression retest

| period | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 141 | 30.50% | 0.515 | -5,056.16 |
| 2024 | 131 | 29.77% | 0.782 | -4,951.01 |
| 2025 | 121 | 30.58% | 0.863 | -3,247.26 |
| 2026_01_07 | 92 | 39.13% | 0.975 | -333.94 |
| COMBINED_2024_2026_07 | 344 | 32.56% | 0.857 | -8,532.20 |
| RECENT_2026_07 | 9 | 22.22% | 0.544 | -494.88 |

### H1 trend × previous D1 sweep

| period | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 7 | 0.00% | 0.000 | -670.46 |
| 2024 | 0 | — | — | +0.00 |
| 2025 | 1 | 0.00% | 0.000 | -1,334.52 |
| 2026_01_07 | 2 | 0.00% | 0.000 | -668.60 |
| COMBINED_2024_2026_07 | 3 | 0.00% | 0.000 | -2,003.13 |
| RECENT_2026_07 | 1 | 0.00% | 0.000 | -249.70 |

### previous D1 sweep × ATR exhaustion

| period | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 25 | 28.00% | 0.476 | -1,026.99 |
| 2024 | 31 | 35.48% | 1.002 | +10.53 |
| 2025 | 28 | 32.14% | 0.525 | -4,212.24 |
| 2026_01_07 | 16 | 31.25% | 1.228 | +769.76 |
| COMBINED_2024_2026_07 | 75 | 33.33% | 0.820 | -3,431.94 |
| RECENT_2026_07 | 1 | 100.00% | ∞ | +298.58 |

### pullback → compression retest

| period | trades | 勝率 | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 79 | 27.85% | 0.430 | -3,425.51 |
| 2024 | 75 | 32.00% | 0.869 | -1,582.30 |
| 2025 | 61 | 34.43% | 0.977 | -274.36 |
| 2026_01_07 | 52 | 40.38% | 0.927 | -513.82 |
| COMBINED_2024_2026_07 | 188 | 35.11% | 0.924 | -2,370.47 |
| RECENT_2026_07 | 3 | 33.33% | 0.624 | -150.77 |

## Robustness / gate diagnostics

| family | 最大winner除外PF | double-cost PF | 最大プラス月比率 | top5 winner比率 | frequency | final |
|---|---:|---:|---:|---:|---|---|
| H1 trend × compression retest | 0.829 | 0.749 | 0.128 | 0.133 | PASS | REJECT |
| H1 trend × previous D1 sweep | 0.000 | 0.000 | — | — | FAIL | REJECT |
| previous D1 sweep × ATR exhaustion | 0.689 | 0.747 | 0.160 | 0.399 | PASS | REJECT |
| pullback → compression retest | 0.873 | 0.805 | 0.139 | 0.210 | PASS | REJECT |

## 方向別

| family | direction | trades | PF | net USD |
|---|---|---:|---:|---:|
| H1 trend × compression retest | LONG | 173 | 0.834 | -4,842.99 |
| H1 trend × compression retest | SHORT | 171 | 0.879 | -3,689.21 |
| H1 trend × previous D1 sweep | LONG | 2 | 0.000 | -1,584.22 |
| H1 trend × previous D1 sweep | SHORT | 1 | 0.000 | -418.91 |
| previous D1 sweep × ATR exhaustion | LONG | 36 | 0.918 | -831.68 |
| previous D1 sweep × ATR exhaustion | SHORT | 39 | 0.709 | -2,600.26 |
| pullback → compression retest | LONG | 93 | 0.874 | -1,909.23 |
| pullback → compression retest | SHORT | 95 | 0.971 | -461.24 |

## causal volatility別（診断のみ）

| family | regime | trades | PF | net USD |
|---|---|---:|---:|---:|
| H1 trend × compression retest | HIGH | 121 | 1.082 | +1,937.83 |
| H1 trend × compression retest | LOW | 223 | 0.710 | -10,470.03 |
| H1 trend × previous D1 sweep | HIGH | 3 | 0.000 | -2,003.13 |
| previous D1 sweep × ATR exhaustion | HIGH | 61 | 0.704 | -5,121.80 |
| previous D1 sweep × ATR exhaustion | LOW | 14 | 1.953 | +1,689.86 |
| pullback → compression retest | HIGH | 64 | 1.050 | +630.75 |
| pullback → compression retest | LOW | 124 | 0.837 | -3,001.22 |

一部sliceではPF 1を超えたが、結果後にhigh/low volatilityだけを残すことは禁止されているため救済しない。特にD1 sweep × ATR exhaustionのLOWは14件のみで、正式候補ではない。

## Base 4 combinationのglobal one-position audit

| period | trades | 勝率 | PF | net USD | Max DD |
|---|---:|---:|---:|---:|---:|
| 2023_SANITY | 177 | 28.81% | 0.485 | -6,815.28 | 6,936.19 |
| 2024 | 163 | 30.67% | 0.806 | -5,804.43 | 6,626.03 |
| 2025 | 153 | 30.72% | 0.737 | -9,036.84 | 10,045.81 |
| 2026_01_07 | 111 | 36.94% | 0.973 | -478.64 | 3,816.38 |
| COMBINED_2024_2026_07 | 427 | 32.32% | 0.813 | -15,319.91 | 17,699.18 |
| RECENT_2026_07 | 12 | 25.00% | 0.562 | -691.86 | 1,032.31 |

## causal・live再現監査

- combination事前登録を結果前にGitHubへcommit
- source candidate fieldsはentry時点で既知の項目だけ
- open/as-of/future OHLC、future ATR、future H1状態、future exit/PnL不使用
- exact M1欠損candidateのみ無効。今回の組み合わせ候補では欠損0件
- entry後の欠損区間はposition継続、人工M1なし、existing M1本数のみholdに計上
- one-positionはcombination familyごと。cross-family global one-positionはaudit-only
- unresolved trade 0
- Stage55変更なし

## 最終境界

- fresh Prospective Shadow: 作成しない
- 結果後の第5組み合わせ追加: しない
- high/low volatility、方向、月だけの救済: しない
- MT5 orders / live trading / live-ready / final signal / Discord: OFF
- Stage55: 稼働系統を変更していない
