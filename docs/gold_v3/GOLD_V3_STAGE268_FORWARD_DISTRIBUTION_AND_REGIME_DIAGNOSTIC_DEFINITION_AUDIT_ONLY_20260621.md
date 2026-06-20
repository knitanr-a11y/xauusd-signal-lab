# GOLD V3 Stage268 定義固定
## Forward distribution and regime diagnostic

作成日: 2026-06-21  
状態: `GOLD_V3_268_FORWARD_DISTRIBUTION_AND_REGIME_DIAGNOSTIC_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage267の全H1/H4 decision forward pathを使い、売買ルールを作る前に、どの市場状態・時間帯・horizonで将来分布が変化するかを診断する。

Stage268ではentry、exit、SL、TP、gate、portfolioを作らない。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- CSV各行は確定足、`time`はOPEN時刻。
- H1情報はtime+1時間、H4はtime+4時間、D1はtime+1日から利用可能。
- `source_close_time <= decision_time`のみ。
- 形成中足のOHLCを使わない。
- M1 sourceは`GOLD_HASH_2025`と`GOLDSHARP_2026`を分離。
- 2025/2026全期間は診断用。live validationとは呼ばない。
- strategy候補を結果後に追加しない。
- C1/F12その他旧候補は`REFERENCE_ONLY_NOT_VALIDATED`のまま。
- live promotion禁止。

## 対象

- H1 source-covered activated decisions全件
- H4 source-covered activated decisions全件
- horizon: 4、8、12、24、48、72、120取引時間

return・MFE・MAEはdecision timeframe ATR14で正規化する。

## decision-time features

### timeframe指標

- EMA20、EMA50
- EMA20 slope 3 bars / ATR14
- ATR14、ATR50、ATR14/ATR50
- ATR percentile100
- true range / ATR14
- body / ATR14
- body / range
- close location value
- upper/lower wick / range
- RSI14
- MACD histogram / ATR14
- recent return 1、3、6 bars / ATR14
- closeのrecent 20-bar range position

### D1 context

- D1 EMA20/EMA50方向
- D1 EMA20 slope 3 bars / D1 ATR14
- D1 ATR14/ATR50
- D1 RSI14
- D1 MACD histogram / ATR14
- D1 close-EMA20 / ATR14

### H1追加context

H1 decisionには利用可能な最新H4 contextをas-ofで付与する。

- H4 EMA方向
- H4 EMA spread / ATR
- H4 slope
- H4 ATR ratio
- H4 RSI/MACD

### execution context

- decision hour UTC
- 4-hour hour-bin: 00-03、04-07、08-11、12-15、16-19、20-23
- weekday
- exact activation / observed closure後activation
- activation delay bucket: 0、1-30、31-90、91分以上

## 固定regime分類

### volatility bucket

ATR percentile100:
- LOW: <=0.25
- MID: 0.25〜0.75
- HIGH: >=0.75

### bar expansion state

- COMPRESSION: true range / ATR14 <=0.70 かつ ATR14/ATR50 <=0.95
- NORMAL: 上記以外で true range / ATR14 <1.30
- EXPANSION: true range / ATR14 >=1.30 または ATR14/ATR50 >=1.10

### timeframe trend state

directionはEMA20-EMA50の符号。

- RANGE: |EMA20-EMA50|/ATR14 <=0.25
- WEAK_TREND: spread 0.25〜0.75かつEMA20 slopeがdirectionと同符号
- STRONG_TREND: spread >0.75かつEMA20 slopeがdirectionと同符号
- CONFLICT: spread>0.25だがEMA20 slopeが逆符号または0

### D1/H4 alignment

- ALIGNED: timeframe directionとD1 directionが同じ
- OPPOSED: 逆
- D1_RANGE: D1 spread<=0.25 D1 ATR

H1では別途H1/H4/D1の3階層状態を出す。

### extension bucket

trend directionに揃えた`close-EMA20` / ATR14:
- PULLBACK_OR_BELOW: <=0.25
- HEALTHY_EXTENSION: 0.25〜1.00
- EXTENDED: 1.00〜2.00
- EXTREME: >2.00

### candle state

- STRONG_DIRECTIONAL: body/range>=0.60かつclose locationが方向側>=0.75
- REJECTION: adverse wick/range>=0.45
- INDECISION: body/range<=0.30
- NORMAL_CANDLE: その他

## 診断direction hypotheses

売買ルールではなく、将来分布を方向整列するための仮説。

1. `BAR_CONTINUATION`: 完了足の方向
2. `TIMEFRAME_TREND`: timeframe EMA20-EMA50方向。RANGEは対象外
3. `D1_TREND`: D1方向。D1_RANGEは対象外
4. `MEAN_REVERSION`: extensionがEXTENDED/EXTREMEのときtimeframe trendと逆方向

各hypothesisでaligned return、MFE、MAEを計算する。

## 単独軸診断

以下の各category×horizon×hypothesisを集計する。

- decision hour
- hour-bin
- weekday
- activation state
- volatility bucket
- expansion state
- trend state
- D1 alignment
- extension bucket
- candle state
- H1/H4/D1 alignment state

出力:

- n
- positive rate
- mean / median ATR-normalized return
- q25 / q75 return
- median MFE / MAE
- median MFE / |median MAE|
- 2025 mean/median/positive rate
- 2026 mean/median/positive rate
- source sign stability

## 固定interaction診断

- trend state × extension bucket
- trend state × volatility bucket
- D1 alignment × volatility bucket
- expansion state × trend state
- candle state × trend state
- hour-bin × volatility bucket
- activation state × hour-bin
- H1/H4/D1 alignment × extension bucket

## path timing分類

各hypothesisについて:

- IMMEDIATE: 8h return>0かつ24h return>0
- DELAYED: 8h return<=0かつ48h return>0
- FADE: 8h return>0かつ48h return<=0
- PERSISTENT: 8h、24h、48h全て>0
- LATE_REVERSAL: 24h<=0かつ72h>0
- NO_DIRECTION: その他

regime別に比率を出す。

## researchable distribution cell基準

これはstrategy合格ではなく、Stage269で研究対象にできる分布セルの基準。

- H1 n>=120、H4 n>=40
- 各source n>=15
- positive rate>=55%
- median aligned return>=0.15 ATR
- meanとmedianが2025/2026両方で同符号
- median MFE / |median MAE| >=1.20
- 隣接する2つ以上のhorizonでmedian returnが同符号
- top hour share<=60%

基準を通っても売買戦略とは呼ばない。

## Stage268合格条件

- H1/H4 feature merge coverage>=99%
- D1 as-of violation 0
- H1のH4 as-of violation 0
- ATR正規化のfinite率>=99%
- 単独軸・interaction・path timingが全て生成
- source分割集計が全セルで再現可能
- 旧候補を採用状態へ戻さない

## 次段階

Stage269ではresearchable distribution cellだけを対象に、entry familyを定義する前に:

- horizon profile
- path timing
- MFE/MAE到達順序
- direction仮説間の差

を比較し、短期型・遅延型・multi-day型へ分ける。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
