# GOLD V3 Stage270 2025–2026 Regime Difference / Recency Decay Audit

作成日: 2026-06-21  
正式状態: `GOLD_V3_270_2025_2026_REGIME_DIFFERENCE_AND_RECENCY_DECAY_COMPLETE_AUDIT_ONLY`

## 結論

2025年と2026年は、同じGOLD相場でも構造が大きく異なる。

季節性を揃えた2025-01-13〜06-19と2026-01-13〜06-19の比較では:

- 2025: price +25.23%、D1 LONG 97.38%、D1 SHORT 0%
- 2026: price -9.32%、D1 LONG 44.24%、D1 SHORT 45.98%、D1 RANGE 9.78%
- H1 ATR/price: 0.301% → 0.469%
- H4 ATR/price: 0.616% → 0.951%
- H4 STRONG_TREND: 53.18% → 41.57%
- H4 WEAK_TREND: 9.60% → 21.30%
- H4 COMPRESSION: 9.45% → 17.60%
- H1/H4/D1 all-aligned: 46.66% → 32.52%

したがって2025は一方向の持続上昇trend、2026は高い基礎volatilityの中でcompression、range、方向転換が増えた相場だった。

2025で強かったtrend型を2026へそのまま持ち込むと、全体平均はプラスでもLONG/SHORTのどちらかが崩れる。

## 比較方法

主要判断は以下の季節一致windowを使用した。

- 2025-01-13〜2025-06-19
- 2026-01-13〜2026-06-19

2025通年 vs 2026利用可能期間は補助診断とした。

価格水準差をedgeと誤認しないよう、forward return、MFE、MAE、trend strengthはATR正規化した。

## 2025と2026の主要差

| 項目 | 2025 matched | 2026 matched | 変化 |
|---|---:|---:|---:|
| H1価格変化 | +25.23% | -9.32% | -34.55pp |
| H1 ATR/価格 | 0.301% | 0.469% | +0.168pp |
| H4 ATR/価格 | 0.616% | 0.951% | +0.335pp |
| H4 STRONG_TREND | 53.18% | 41.57% | -11.61pp |
| H4 WEAK_TREND | 9.60% | 21.30% | +11.70pp |
| H4 RANGE | 14.62% | 17.90% | +3.28pp |
| H4 COMPRESSION | 9.45% | 17.60% | +8.15pp |
| H1 LOW volatility | 28.33% | 36.31% | +7.98pp |
| D1 LONG | 97.38% | 44.24% | -53.14pp |
| D1 SHORT | 0.00% | 45.98% | +45.98pp |
| H1/H4/D1 all-aligned | 46.66% | 32.52% | -14.14pp |
| H1/H4/D1 any-range | 17.83% | 28.34% | +10.51pp |

### 高volatilityなのにLOW volatilityが増えた理由

矛盾ではない。

- ATR/価格は2026の方が高く、市場全体の基礎volatilityは上昇
- `LOW volatility`は直近100本内の相対順位
- 2026は高いvolatility水準の中で、圧縮期間と急拡大期間を交互に繰り返した

つまり2026は静かな相場ではなく、**高volatilityを背景にしたstop-and-go型**だった。

## 数値featureのdrift

季節一致H1比較のPSI上位:

| Feature | 2025 median | 2026 median | PSI |
|---|---:|---:|---:|
| H1 ATR14 | 9.40 | 22.42 | 9.94 |
| D1 EMA20 slope / ATR | +0.404 | +0.008 | 2.27 |
| D1 EMA spread / ATR | 1.619 | 0.901 | 2.00 |
| D1 RSI14 | 61.29 | 49.03 | 1.76 |
| D1 MACD hist / ATR | +0.0565 | -0.0423 | 0.68 |
| H4 ATR ratio | 0.992 | 0.957 | 0.46 |
| H4 RSI14 | 56.62 | 50.10 | 0.31 |

特にD1 slope、spread、RSI、direction構成の変化が大きい。2025の上位足持続trendが2026では消え、方向転換と中立化が進んだ。

## 2026年内の相場遷移

| 月 | 価格変化 | D1状態 | H1特徴 |
|---|---:|---|---|
| 1月 | +4.97% | LONG 100% | strong trend 67.6%、high vol 50.9% |
| 2月 | +11.80% | LONG 100% | low vol 50.9%、compression 23.6% |
| 3月 | -13.07% | 上昇trend崩壊中 | all-aligned 6.9%、ATR/price 0.659% |
| 4月 | -1.17% | SHORT 66.7% | range 29.0%、all-aligned 12.6% |
| 5月 | -2.19% | SHORT 100% | range 28.4% |
| 6月 | -8.47% | SHORT 100% | strong trend 50.3%、all-aligned 51.8% |

2026年は1〜2月の上昇、3〜4月の転換、5〜6月の下降という3局面に分かれる。

## R1: H1 weak trend × low volatility / 48h

### 年比較

| 期間 | n | Positive | Mean | Median | MFE/MAE |
|---|---:|---:|---:|---:|---:|
| 2025 | 362 | 67.96% | +3.198 ATR | +2.983 ATR | 2.30 |
| 2026 | 208 | 53.85% | +0.957 ATR | +0.291 ATR | 0.94 |

2025から大幅に劣化した。

2025はD1 LONG 96.69%、2026はD1 LONG 34.13%、SHORT 51.92%。D1 spread中央値は1.367ATRから0.409ATR、D1 slopeは+0.126から+0.035へ低下した。

### 直近

最新60日:

- n=58
- mean +2.504ATR / median +2.150ATR
- LONG n=16: mean -4.488 / median -4.514
- SHORT n=42: mean +5.168 / median +5.370

最新30日:

- overall mean -0.434 / median +0.199
- LONG mean -4.307
- SHORT mean +2.215

全体値は良く見えるが、利益はSHORTへ完全に偏っている。対称的なregimeとしては現在不安定。

正式判定: `CURRENTLY_UNSTABLE`

## R2: H1 UTC08-11 × high volatility / bar continuation / 48h

### 年比較

| 期間 | n | Positive | Mean | Median | MFE/MAE |
|---|---:|---:|---:|---:|---:|
| 2025 | 197 | 54.15% | +0.863 ATR | +0.746 ATR | 1.53 |
| 2026 | 107 | 57.94% | +1.388 ATR | +0.861 ATR | 1.62 |

R1と違い、2026で弱化していない。

R2はD1 trend方向ではなく、その時点のH1高volatility impulse方向を使うため、2025の一方向bull trendへの依存が比較的小さい。

### 直近

最新90日:

- n=48
- mean +0.632 / median +0.365
- LONG mean +1.026 / median +0.284
- SHORT mean +0.238 / median +0.564

最新60日:

- n=34
- mean +1.086 / median +0.567
- LONG mean +1.133 / median -0.397
- SHORT mean +1.045 / median +0.975

最新30日:

- n=20
- mean +1.776 / median +4.877
- LONG mean +2.902
- SHORT mean +0.855、median -0.790

平均は両方向プラスだが、方向別中央値が交互に弱くなる。現在残る中では最も良いが、live-readyではない。

正式判定: `CURRENTLY_MAINTAINED`  
追加警告: `DIRECTION_DIVERGENCE`

## R3: H1 indecision × range / 8h

### 年比較

| 期間 | n | Positive | Mean | Median | MFE/MAE |
|---|---:|---:|---:|---:|---:|
| 2025 | 159 | 56.60% | +0.206 ATR | +0.155 ATR | 1.28 |
| 2026 | 72 | 59.72% | +0.253 ATR | +0.431 ATR | 1.77 |

2026全体では改善した。H1 RANGE比率が14.36%から18.99%、compressionが11.93%から15.58%へ増え、R3が発生しやすい環境になった。

### 直近

最新60日:

- n=33
- mean +0.624 / median +0.748
- LONG n=6: mean -0.215 / median -0.506
- SHORT n=27: mean +0.810 / median +0.767

最新30日:

- n=14
- LONG mean -0.077
- SHORT mean +0.506

全体はプラスだが、直近はSHORT中心。R1ほど崩れてはいないが、対称性は弱い。

正式判定: `WEAKENED_BUT_POSITIVE`

## path timingの変化

### R1

- 2025 PERSISTENT 40.6%、FADE 7.2%
- 2026 PERSISTENT 29.8%、FADE 23.6%
- 最新30日 FADE 31.2%

2026はtrendが続かず、途中まで伸びて反転する比率が大幅に増えた。R1劣化の直接的なpath特徴。

### R2

- 2025 PERSISTENT 31.7%、DELAYED 16.1%
- 2026 PERSISTENT 32.7%、DELAYED 21.5%
- 最新60日 DELAYED 35.3%

persistent比率は維持し、最近は遅れて伸びる比率が増えた。固定短期exitでは取り逃がす。

### R3

- 2025 PERSISTENT 31.9%
- 2026 PERSISTENT 30.6%
- 最新60日 PERSISTENT 39.4%

R3の構造自体は維持しているが、直近方向がSHORTへ偏っている。

## 正式判断

1. 2025と2026は同じregimeではない。
2. 2025のtrend優位は、ほぼ一方向のD1 bull marketによる部分が大きい。
3. R1は2026全体で弱化し、直近はSHORTだけが利益を出すため現在不安定。
4. R2は2026および直近90/60日で最も維持されている。
5. R3は2026全体では有効だが、直近はSHORT偏重。
6. LONGだけを停止、SHORTだけを採用する後付け処理は行わない。
7. 方向崩壊を生むmarket-state featureを次段階で診断する。
8. 2026を使用済みのため、いずれもclean live validationではない。

## 次段階

Stage271では新triggerを増やさず、R2を第一対象、R3を第二対象にする。

- R2: direction divergenceが発生する前兆をentry-known featureで診断
- R3: recent LONG failureの原因を診断
- R1: research-onlyへ格下げし、対称regimeとしての開発を停止
- M15 false-break near-leadはR3の方向安定性問題が解消するまで昇格しない
- pre-2025 M15/M5/M1取得までは新trigger探索を停止

## correctness

- 2025/2026 matched windowを固定
- source identity維持
- ATR正規化path使用
- numeric/categorical drift生成
- monthly/rolling/latest30/latest60生成
- 旧候補status維持
- regression tests: 4/4 PASS
- Stage270 acceptance criteria: ALL PASS

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
