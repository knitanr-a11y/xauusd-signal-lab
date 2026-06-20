# GOLD V3 Stage266B 定義固定
## Deep win/loss pattern analysis + family-specific loss gates

作成日: 2026-06-21  
状態: `GOLD_V3_266B_DEEP_WIN_LOSS_PATTERN_AND_FAMILY_GATE_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

C1/C2/C3それぞれについて、勝ち群と負け群を多角的に比較し、負けに偏るentry-known状態をfamily専用gateへ変換する。改善したfamilyだけを後段portfolioへ積み上げる。

## 絶対契約

- audit-only。
- CSV各行は確定足、`time`はOPEN時刻。
- M1=time+1分、H1=time+1時間、H4=time+4時間、D1=time+1日から利用。
- `source_close_time <= decision_time`のみ。
- raw candidate・resolved outcome・gate rejectedを全件保存。
- 個別負けtradeの手動削除禁止。
- outcome、exit理由、MFE/MAE、fill後情報をgate featureへ使わない。
- fill M1の確定high/low/closeをgateに使わない。
- 正式評価は月次expanding walk-forward OOFのみ。
- 2025/2026全期間fitの結果はpattern discovery診断であり正式成績にしない。
- LONG only、SHORT only、年別除外、結果後の閾値変更禁止。
- live promotion禁止。

## 分析軸

各familyを以下の視点で分解する。

1. 上位足trend strength
   - H4 EMA20-EMA50 / ATR14
   - D1 EMA20-EMA50 / D1 EMA50
   - H4 EMA20 slope / ATR14
   - D1 EMA20 slope / D1 ATR14

2. setup geometry
   - order distance / ATR14
   - channel width / ATR14
   - recent 10・20 H4 range内のclose位置
   - breakout boundaryへの過去接触回数
   - boundary age

3. candle structure
   - aligned body / ATR14
   - body / range
   - aligned wick / range
   - adverse wick / range
   - close location value
   - inside / outside bar
   - NR4 / NR7
   - overlap ratio

4. momentum and acceleration
   - aligned return 1・2・3・6 H4 / ATR14
   - return acceleration
   - RSI14 aligned
   - MACD histogram aligned / ATR14
   - directional close streak

5. volatility regime
   - ATR14 / ATR50
   - ATR percentile over past 100 H4
   - range / ATR14
   - Bollinger width / ATR14
   - expansion after compression

6. H1 internal state at decision_time
   - latest completed H1 return 1・4・8 hours / H1 ATR14
   - H1 EMA20-EMA50 spread / H1 ATR14
   - H1 close location in recent 8-hour range
   - H1 directional streak
   - H1 ATR14 / ATR50

7. participation and execution-known context
   - H4 tick_volume / rolling median
   - H4 spread / rolling median
   - weekday
   - decision hour
   - family overlap count at same decision_time

## descriptive diagnostics

familyごとに以下を出す。

- win/loss count
- standardized mean difference
- point-biserial correlation
- quartile-bin win rate・expectancy・count
- 2025/2026でeffect方向が一致するか
- LONG/SHORTでeffect方向が一致するか
- top adverse特徴のpairwise intersection
- max_depth=2、min_samples_leaf=10の説明用decision tree

説明用treeは正式gateには直接使わない。

## family-specific gate

familyごとに独立モデルを作る。

### feature selection

各月のtraining内だけで実施。

- numeric featureの単変量AUCを計算
- training前半・後半で勝敗方向が一致
- |AUC-0.5| >= 0.04
- 欠損率20%以下
- 相関|r|>0.85のfeature群はAUC最大1つだけ残す
- 最大8 feature

### model

- median imputer
- RobustScaler
- LogisticRegression elastic-net
- penalty=elasticnet
- solver=saga
- C=0.2
- l1_ratio=0.5
- class_weight=balanced
- max_iter=5000
- random_state=266

### monthly OOF

- 当月開始前にexit済みの同family tradeだけで学習
- minimum training:
  - C1=60
  - C2=40
  - C3=24
- threshold候補はtraining prediction retention 50%、65%、80%
- training上でcost5 expectancy最大を選択
- 同点はretentionが高い方
- training cost5 expectancyが全候補で0以下なら80% retention
- thresholdは当月固定

## gate合格条件

familyごとに:

- OOF accepted 25件以上
- retention 40〜85%
- accepted cost2 win rate > raw OOF win rate
- accepted cost5 expectancy > raw OOF cost5 expectancy
- accepted cost5 PF >= 1.20
- accepted expectancy > rejected expectancy
- 2025/2026でgate effect方向が一致
- LONG/SHORTでgate effect方向が一致、または片方向10件未満なら未合格
- accepted上位5trade利益依存 <= 60%

## stackへの追加条件

上記を満たしたfamilyだけをstack候補へ追加する。

- gate不合格familyは追加しない
- familyごとのgate probabilityをdecision_timeで固定
- one pending / one active
- 同時刻はprobability降順
- suppressed候補を台帳へ残す

## 解釈

勝率改善を優先するが、取引数を過度に減らして見かけだけ良くするgateは不合格。勝率・期待値・PF・retention・期間安定性を同時に要求する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
