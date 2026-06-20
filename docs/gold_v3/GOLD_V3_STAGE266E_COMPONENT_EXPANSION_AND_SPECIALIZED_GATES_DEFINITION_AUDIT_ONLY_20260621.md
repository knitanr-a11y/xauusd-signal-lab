# GOLD V3 Stage266E 定義固定
## Frozen C1 + specialized C2 + raw C3 + new C4/C5 components

作成日: 2026-06-21  
状態: `GOLD_V3_266E_COMPONENT_EXPANSION_AND_SPECIALIZED_GATES_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

勝率改善済みC1を固定componentとして保持し、C2をcost5勝率専用gateで再改善する。C3はgateを掛けずraw監視とし、取引頻度を増やす新候補C4/C5を追加する。各familyは独立に勝敗パターンを分析し、月次walk-forward OOFで改善したものだけをstackする。

## 絶対契約

- audit-only。
- CSV各行は確定足、`time`はOPEN時刻。
- M1=time+1分、H1=time+1時間、H4=time+4時間、D1=time+1日から利用。
- source_close_time <= decision_timeのみ。
- candidate・gate rejected・suppressedを全件保存。
- 個別負けtradeの手動削除禁止。
- gate featureはpending注文作成時点で既知の情報だけ。
- future outcome、exit理由、fill後M1、MFE/MAEはgateに使わない。
- LONG only、SHORT only、年別除外禁止。
- 2025/2026全期間fitのin-sample成績は正式評価にしない。
- 正式評価は月次expanding walk-forward OOFのみ。
- live promotion禁止。

## 共通context

LONG:
- 利用可能な最新D1 EMA20 > EMA50
- 完了H4 EMA20 > EMA50
- 完了H4 close > EMA20

SHORTは完全反転。

## 共通execution

- decision hours UTC 00, 04, 08
- pending expiry 4時間
- M1 gap/touchでfill
- LONG gap fill=max(stop,M1 open)
- SHORT gap fill=min(stop,M1 open)
- SL=1.25 ATR14
- TP=2.5 ATR14
- 最大保有8時間
- UTC20:00を越えるfillはblock
- same M1はSL優先
- one setup one trade

## components

### C1_CHANNEL6_FROZEN

Stage266Dの方法とOOF gate判定を固定する。

- stop=直近6本完了H4の方向側境界
- Stage266D win-rate-first family gate
- parameter、feature selection、threshold selectionを変更しない

### C2_PULLBACK_COST5_GATE

setupはC2と同じ。

- 直近3本でEMA20への押し/戻りが存在
- stop=直近2本完了H4の方向側境界

専用gate:
- target=`cost5_pnl > 0`
- C2専用feature universe
  - H4 20-bar方向位置
  - H4 body/range
  - H4 adverse/favorable wick
  - H4 ATR14/ATR50
  - H4 volume ratio
  - H4 2-bar return/ATR
  - H1 EMA20 slope aligned
  - H1 1/4/8h return aligned
  - H1 range/ATR
  - family overlap count
  - channel width/ATR
- monthly training only
- minimum train 40
- retention候補30/40/50/60/70/80%
- trainingでcost5 win rate>=60%、cost5 expectancy>0、minimum accepted20を満たす最大retention
- 該当なしはcost5 win rate最大、同点はcost5 expectancy、さらに同点はretention最大

### C3_COMPRESSION_RAW

- Stage266Dでgateがraw勝率を悪化させたためgateを使用しない
- raw OOF監視のみ
- stack追加条件を満たすまでportfolioへ入れない

### C4_PREVIOUS_BAR_BREAKOUT

頻度確保用の広いH4 continuation候補。

- 共通contextのみ
- LONG stop=最新完了H4 high
- SHORT stop=最新完了H4 low
- pullback/compression条件なし

専用gate:
- Stage266D win-rate-first family gate
- target=`cost2_pnl > 0`
- minimum train80
- retention候補30/40/50/60/70/80%
- trainingでcost2 win rate>=60%、cost2 expectancy>0、cost5 expectancy>0、minimum accepted30を満たす最大retention

### C5_INSIDE_BAR_BREAKOUT

構造候補。

- 最新完了H4 high <= 1本前H4 high
- 最新完了H4 low >= 1本前H4 low
- LONG stop=最新完了H4 high
- SHORT stop=最新完了H4 low

専用gate:
- target=`cost2_pnl > 0`
- minimum train30
- retention候補40/50/60/70/80%
- trainingでcost2 win rate>=60%、cost5 expectancy>0、minimum accepted15を満たす最大retention

## entry-known feature universe

- direction
- H4 body/ATR、body/range、favorable/adverse wick
- H4 close location
- H4 EMA20/EMA50 spread・slope
- D1 EMA spread・slope・RSI・MACD
- H4 RSI・MACD
- H4 1/2/3/6-bar aligned return
- ATR14/ATR50、ATR percentile100
- Bollinger width/ATR
- volume/spread ratio
- H4 recent range内方向位置
- H1 1/4/8h aligned return
- H1 EMA spread・slope
- H1 RSI・MACD・ATR ratio・range/ATR
- H1 recent range内方向位置・streak
- order distance/ATR
- channel width/ATR
- boundary touch count・age
- family overlap count
- weekday・decision hour

## family qualification

- OOF accepted 25件以上
- retention 30〜85%
- cost2 win rate >=60%
- cost2 raw比+5 percentage point以上
- cost5 win rate >=55%
- cost5 expectancy>0
- cost5 PF>=1.25
- accepted expectancy > rejected expectancy
- 2025/2026両sourceでaccepted expectancy>=0
- LONG/SHORT各10件以上かつexpectancy>=0
- top5 positive profit share<=60%

C3 raw qualification:
- resolved30件以上
- cost2 win rate>=60%
- cost5 win rate>=55%
- cost5 PF>=1.25
- LONG/SHORT各10件以上
- 2025/2026両sourceプラス
- top5 share<=60%

## stacked portfolio

qualificationを通ったcomponentだけを使用。

- C1は固定component
- C2/C4/C5は各family合格時のみ追加
- C3はraw qualification通過時のみ追加
- one pending / one active
- first come
- 同時刻はgate probability降順
- 同scoreはC5 > C2 > C1 > C4 > C3
- suppressed候補を全件保存

## portfolio目標

- OOF resolved100件以上
- 月間中央値6件以上
- cost2 win rate>=60%
- cost5 win rate>=55%
- cost5 expectancy>=2.5 USD/oz
- cost5 PF>=1.25
- LONG/SHORT各30件以上
- 2025/2026両sourceプラス
- top5 profit share<=50%
- max drawdown<=gross profit

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
