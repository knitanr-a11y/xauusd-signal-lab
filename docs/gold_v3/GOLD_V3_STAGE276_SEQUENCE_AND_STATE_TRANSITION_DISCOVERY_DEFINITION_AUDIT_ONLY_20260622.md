# GOLD V3 Stage276 定義固定
## Sequence and State Transition Discovery

作成日: 2026-06-22  
状態: `GOLD_V3_276_SEQUENCE_AND_STATE_TRANSITION_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage275で不合格だったstatic snapshot cellを再調整せず、M15直近32〜64本の順序情報、volatility transition、H1/H4 trend transition、state dwellをentry-known情報だけで表現し、別ベクトルの候補edgeを探索する。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない・使わない・fallbackしない。
- CSVの全行は確定足。`time`はbroker server bar OPEN時刻。
- M15 decisionは`time + 15m`。
- H1は`time + 1h <= decision_time`、H4は`time + 4h <= decision_time`のみ使用。
- entryはdecision以後の最初の同source M1 open。
- future path、MFE、MAE、TP/SL結果をfeatureへ入れない。
- same M1 TP/SLはSL優先。
- 欠損の補間、nearest future、別source fallback禁止。
- 2025/2026を2024 discovery選択に使わない。
- LONG/SHORTを同じfeature/model/ruleで扱う。
- 候補poolを結果を見て手動削除しない。
- live、final signal、MT5注文、Discord通知、partial closeは禁止。

## データ分割

- Initial model train: 2023-03-01〜2023-09-30のresolved-only行
- Score calibration: 2023-10-01〜2023-12-31
- Discovery: 2024
- Confirmation: 2025
- Final/current diagnostic: 2026末尾まで

2024以降は月初に、その月初までにresolvedとなった過去行だけでSGDを1回更新するexpanding monthly walk-forwardとする。

## Sequence / finite-state feature

方向展開前の主な状態:

- M15 return 1/2/4/8/16/32/64本
- bar sign run length
- up-bar share 8/16/32/64
- sign transition count 8/16/32/64
- range mean 8/16/32/64 / ATR
- past high/low distance 8/16/32/64 / ATR
- ATR14/ATR50と4本変化
- EMA20/50 distance、EMA20 slope
- compression state
- compression後8本以内のexpansion state
- volatility-state dwell
- closed H1/H4 trend state
- H1 transition age
- H1/H4 agreement
- broker server hour / weekday sin-cos

LONG/SHORTへ展開後、方向性featureをdirection aligned表現へ変換する。最終feature数は48。

2023-only固定閾値:

- compression q20/q30
- M15 range/ATR q70/q75/q80
- absolute body/ATR q70/q80

## Label

2つのmodelを同じ48featureで学習する。

1. Quality label
   - entry後480 same-source M1 row以内
   - +1.0ATRが-0.75ATRより先
   - same M1成立はadverse-first
2. Positive label
   - entry後240 same-source M1 row終点のdirectional return > 0

score:

`0.65 * p(quality) + 0.35 * p(positive)`

## Model family

- `SGD_A1E4`: logistic loss、L2、alpha=1e-4、average=True
- `SGD_A5E4`: logistic loss、L2、alpha=5e-4、average=True

imputation median、mean、stdはinitial 2023 trainだけで固定する。float64を使用する。

## Candidate grid

各decisionでLONG/SHORT scoreを比較し、高い方向だけを候補化する。

- calibration score quantile: Q90 / Q95
- direction score margin: 0.03 / 0.06
- cooldown: 4h / 8h
- execution skeleton:
  - `FAST_15_10_8H`: TP1.5ATR / SL1.0ATR / 480 M1 rows
  - `WIDE_225_40_3H`: TP2.25ATR / SL4.0ATR / 180 M1 rows

2 model × 2 quantile × 2 margin × 2 cooldown × 2 exit = 32 model cells。

## Pre-registered event diagnostics

modelとは別に、次の40 patternを固定生成する。

- Compression → Expansion → First Retest: 16
- Failed Breakout → Reclaim / Rejection: 12
- H1 Transition → First Pullback: 12

各patternを2 execution skeletonで評価し、80 event cellsとする。

合計112 cells。

## 2024 discovery必須条件

- n >= 100
- LONG n >= 30
- SHORT n >= 30
- active months >= 9
- cost0.60 mean > 0
- cost0.60 PF >= 1.30
- cost1.00 PF >= 1.15
- median gross R >= 0
- LONG cost0.60 mean >= 0
- SHORT cost0.60 mean >= 0
- top5 positive-profit share <= 35%

条件を通過したcellだけを変更せず2025へ進める。

## 2025 confirmation

- n >= 50
- cost0.60 mean > 0
- PF >= 1.15
- median gross R >= 0
- LONG/SHORT各 n >= 15、mean >= 0
- positive active-month share >= 50%

## 2026 final/current

- n >= 25
- cost0.60 mean > 0
- PF >= 1.10
- median gross R >= 0
- LONG/SHORT各 n >= 8、mean >= 0

## Live reproducibility gates

成績評価より前に次を必須とする。

1. Prefix feature parity
   - 2024以降64 checkpoint
   - 48feature × LONG/SHORT
   - NaN pattern exact
   - max absolute difference <= 1e-12
2. Model score parity
   - whole batch / chunk64 / one-row
   - max absolute difference <= 1e-12
3. Candidate replay parity
   - 16 model candidate configurations
   - accepted index exact
   - direction exact

不一致が1件でもStage276はBLOCKED。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
