# GOLD V3 Stage274 Liquidity Sweep / Reclaim Structural Family Audit

作成日: 2026-06-21  
正式状態: `GOLD_V3_274_NO_STRONG_MULTI_PERIOD_RESEARCH_LEAD_AUDIT_ONLY`

## 結論

GOLD向けの最有力仮説として、次の2familyを事前固定して検証した。

1. `HTF_TREND_LIQUIDITY_SWEEP_RECLAIM_FIRST_PULLBACK`
2. `RANGE_FAILED_BREAK_RECLAIM_REVERSAL`

データ分割は以下を厳守した。

- 2023〜2024年: 発見期間
- 2025年: 確認期間
- 2026年: 最終・現在判定期間

結果:

- Family A: 発見期間の最大標本11件で`INSUFFICIENT_SAMPLE`
- Family B: 最大106件あったが、全6固定セルでコスト後期待値・PF・中央値の基準を満たさず`NO_DISCOVERY_LEAD`
- 2025年確認へ昇格したセル: 0
- 2026年最終判定へ昇格したセル: 0
- `STRONG_MULTI_PERIOD_RESEARCH_LEAD`: 0

## 固定した検証条件

### Family A

- H4 close > EMA20 > EMA50、または完全反転
- H4 EMA spread / ATR >= 0.35
- H4 EMA20 slope3 / ATR >= 0.10
- 前日高安または直近20本の確定H1 swingをsweep
- M15でlevelをreclaim
- reclaim後1〜4本目の最初のmidpoint pullback
- pullback確定後の次M1 openでentry

### Family B

- H4 EMA20/50 spread <= 0.75 ATR
- H4 EMA20 slope3 <= 0.20 ATR
- 前日高安またはH1 swing20をfalse break
- M15 closeでrange内へreclaim
- 次1〜2本のM15で反対方向確認
- confirmation確定後の次M1 openでentry

共通:

- TP 1.5R / 2.0R / 2.5R
- SLはsweep extreme外0.15 M15 ATR
- 24 trading-hour cap
- 同一M1でTP/SL成立時はSL優先
- variant×direction内24 trading-hour cooldown
- 2 USD/oz cost stress

## Candidate funnel

- 全candidate: 618
- independent accepted: 328
- cooldown suppressed: 290
- 24h path complete candidate: 327
- split yearを跨いだため評価除外: 1 candidate

Family別のraw候補:

- A_PD: 18
- A_H1S20: 17
- B_PD: 267
- B_H1S20: 316

## Family A: trend sweep reclaim first pullback

### A_PD

発見期間independent candidateは11件だけだった。

1.5R:

- n=11
- mean +0.818R
- median +1.500R
- cost2 expectancy +0.997 USD
- PF 1.744

一見良いが:

- 2023 n=8、2024 n=3
- LONG n=10、SHORT n=1
- top5 profit share 90.6%
- discovery minimum n=60を大幅に下回る

2.0R/2.5Rも同様に少数利益へ集中し、方向・年の標本を満たさなかった。

2025年は4件全勝だったが、2026年candidateは0。発見段階の標本不足を2025年4件で救済しない。

判定: `INSUFFICIENT_SAMPLE`

### A_H1S20

発見期間n=10。

- 1.5R cost2 expectancy -0.835 USD、PF 0.757
- 2.0R cost2 expectancy -1.016 USD、PF 0.750
- 2.5R cost2 expectancy -0.148 USD、PF 0.964

2025年も全セルでコスト後マイナス。2026年candidateは0。

判定: `INSUFFICIENT_SAMPLE_AND_NO_COST_EDGE`

## Family B: range failed-break reversal

### B_H1S20 — 発見期間

| TP | n | Mean R | Median R | Cost2 expectancy | PF |
|---|---:|---:|---:|---:|---:|
| 1.5R | 106 | +0.130 | -1.000 | -2.035 USD | 0.523 |
| 2.0R | 106 | +0.183 | -1.000 | -1.961 USD | 0.568 |
| 2.5R | 106 | +0.125 | -1.000 | -2.275 USD | 0.537 |

Gross平均はわずかにプラスだが、典型tradeを示す中央値は全て-1R。2 USD/ozコスト後は全てマイナスで、PFも1未満だった。

2025年も:

- n=40
- cost2 expectancy -2.225〜-1.605 USD
- PF 0.700〜0.821
- median -1R

で確認失敗。

2026年はSHORTだけが良く:

- 2.0R SHORT n=15、mean +0.800R、cost2 +17.028 USD、PF 3.221
- 同LONG n=13、mean -0.788R、cost2 -12.487 USD、PF 0.394

となった。これは2026年下降regimeへの強い方向依存で、両方向signalではない。

直近60日も:

- ALL n=10、2.0R cost2 -7.652 USD、PF 0.473
- LONG n=7、0勝、mean -1R
- SHORT n=3のみ良好

判定: `NO_DISCOVERY_LEAD_CURRENT_SHORT_REGIME_DEPENDENT`

### B_PD — 発見期間

| TP | n | Mean R | Median R | Cost2 expectancy | PF |
|---|---:|---:|---:|---:|---:|
| 1.5R | 70 | +0.187 | -0.138 | -1.287 USD | 0.661 |
| 2.0R | 70 | +0.210 | -1.000 | -1.629 USD | 0.622 |
| 2.5R | 70 | +0.159 | -1.000 | -1.863 USD | 0.604 |

標本数と年・方向件数は満たしたが、コスト後・PF・中央値で不合格。

2025年も:

- n=33
- 全TPでmean Rが負
- cost2 expectancy -3.104〜-4.635 USD
- PF 0.436〜0.555

2026年だけは:

- 2.5R ALL n=19、cost2 +6.924 USD、PF 1.469
- SHORT n=7、mean +2.000R、PF 15.136
- LONG n=12、mean -0.587R、cost2 -10.290 USD

だった。これも現在のSHORT偏重で、2023〜2025年を通らない。

直近60日B_PD 1.5RはALL n=8でcost2 +0.948 USDだが:

- LONG n=6、mean -0.167R、cost2 -7.148 USD
- SHORT n=2、2勝
- top5 profit share 100%

のため強い候補ではない。

判定: `NO_DISCOVERY_LEAD_CURRENT_SHORT_REGIME_DEPENDENT`

## なぜ「2026年SHORTだけ」を採用しないか

2026年のfailed-break SHORTは非常に強く見える。しかし:

- 発見期間2023〜2024年ではコスト後マイナス
- 2025年でもfamily全体がマイナス
- 2026年LONGは大幅マイナス
- 2026年SHORT件数は7〜15件
- latest60 SHORTは2〜3件
- 利益集中率が高い

結果を見てSHORTだけ残すと、2026年下降相場をラベルとして使った後付けになる。

## 正式判断

1. 私が最有力と考えたtrend sweep reclaimは、固定条件では発生頻度が低すぎた。
2. range failed-break reversalは頻度はあるが、2023〜2025年に取引可能なedgeを持たなかった。
3. 2026年のfailed-break SHORT優位は、現在の下降regime依存であり普遍signalではない。
4. thresholdを緩める、時間帯を限定する、SHORTだけ採用する、TPを2026へ合わせることは禁止する。
5. この2familyからstrong multi-period research leadは作れなかった。
6. 手作業で有名patternを順番に追加する研究は、ここで停止すべき。

## 次の研究方向

次は、名前付きpatternを先に決める方法ではなく、全M15 decision universeから:

- 将来8h/24h/48hのMFE/MAE分布
- 2023/2024に共通する上位足context
- 方向対称性
- entry-known featureだけの安定cluster

を抽出する`OUTCOME_FIRST_OPPORTUNITY_MAP`へ移る。

2023〜2024年でclusterを発見し、2025年へ固定適用、2026年を最終判定に残す。clusterが2025/2026で再現しなければ、GOLD自動signal開発自体を停止する判断を含める。

## correctness

- 12 pre-registered cells evaluated
- 2023〜2024 discovery only
- 2025 confirmation not used for selection
- 2026 not used for tuning
- same-bar SL priority
- all/suppressed ledgers retained
- regression tests 4/4 PASS
- live promotion prohibited

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
