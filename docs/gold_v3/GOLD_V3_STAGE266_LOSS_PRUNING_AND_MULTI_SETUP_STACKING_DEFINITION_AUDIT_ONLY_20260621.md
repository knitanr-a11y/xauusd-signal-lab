# GOLD V3 Stage266 定義固定
## Loss-pruning gate + H4 multi-setup stacking

作成日: 2026-06-21  
状態: `GOLD_V3_266_LOSS_PRUNING_AND_MULTI_SETUP_STACKING_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

既存H4 intrabar breakoutの負けを、entry時点で既知の特徴から事前除外するgateへ変換する。同時に、H4の別setup候補を追加し、各setupの勝率を個別に高めてからportfolioへ積み上げる。

## 絶対契約

- audit-only。
- CSV行は確定足、timeはOPEN時刻。
- M1=time+1分、H1=time+1時間、H4=time+4時間、D1=time+1日から利用。
- source_close_time <= decision_timeのみ。
- 負けtradeの個別削除は禁止。
- gateは注文作成時またはfill瞬間に既知の特徴だけを使う。
- M1 bar確定後のhigh/low/closeを同じbarのentry判断に使わない。
- future outcome、exit理由、MFE/MAEをfeatureに使わない。
- candidate台帳は全件保持し、`GATE_ACCEPTED` / `GATE_REJECTED` / 各execution状態を残す。
- 2025/2026全期間へfitしたin-sample勝率を正式成績にしない。
- 正式評価は月次expanding walk-forward OOFのみ。
- LONG only、SHORT only、年別除外、結果後のparameter変更は禁止。
- live promotion禁止。

## candidate families

### C1: H4 six-bar channel continuation
Stage265と同一。

- D1/H4 EMA20-EMA50方向一致
- H4 closeがEMA20の方向側
- LONG stop=直近6本完了H4 high最大
- SHORT stop=直近6本完了H4 low最小

### C2: H4 pullback continuation breakout

- 同じD1/H4方向context
- 直近3本でEMA20への押し/戻りが存在
- LONG stop=直近2本完了H4 high最大
- SHORT stop=直近2本完了H4 low最小

### C3: H4 compression breakout

- 同じD1/H4方向context
- 直近3本high-low幅 <= 1.5 * H4 ATR14
- H4 ATR14 / ATR50 <= 1.0
- LONG stop=直近3本high最大
- SHORT stop=直近3本low最小

## execution contract

- decision hours UTC 00, 04, 08
- pending expiry=4時間
- M1 gap/touchでfill
- gap LONG=max(stop,M1 open)、SHORT=min(stop,M1 open)
- SL=1.25 ATR、TP=2.5 ATR、最大8時間
- 20:00 UTCを越えるfillはblock
- same M1はSL優先
- one setup one trade

## entry-known feature universe

注文作成時:

- family
- direction
- H4 aligned body / ATR14
- H4 range / ATR14
- aligned close-EMA20 / ATR14
- aligned EMA20-EMA50 / ATR14
- aligned D1 EMA20-EMA50 / D1 EMA50
- order stop distance / ATR14
- channel width / ATR14
- ATR14 / ATR50
- aligned H4 1-bar、2-bar、3-bar return / ATR14
- weekday
- decision hour

fill瞬間:

- trigger delay minutes / 240
- gap fill flag
- gap distance / ATR14

禁止feature:

- fill M1の確定close/high/low
- fill後の値動き
- exit information

## loss-pruning model

- target: cost5_pnl > 0
- model: median imputer + StandardScaler + LogisticRegression
- penalty=L2、C=0.25、class_weight=balanced、max_iter=2000、random_state=266
- familyはone-hot
- 月初に再学習
- 当月より前にexit済みのtradeだけをtrainingへ使用
- training最低60trade
- gate thresholdはtraining scoreの30 percentile
- 予測下位30%をrejectし、上位70%をaccept
- warm-up期間は正式OOF成績から除外

## setup別評価

各familyについてOOF accepted群を集計する。

- trade数
- retention rate
- win rate
- cost2/cost5 expectancy
- PF
- LONG/SHORT
- 2025/2026 source
- rejected群との比較

## stacking

OOF accepted候補だけを時系列に統合。

- one active position
- one pending order
- first come
- 同時刻はgate probability降順
- 同scoreはC2 > C3 > C1
- suppressed候補も台帳へ残す

## 合格基準

### family gate

- OOF accepted 30件以上
- retention 35〜80%
- win rate >= 60%
- cost5 expectancy > 0
- cost5 PF >= 1.20
- accepted expectancy > rejected expectancy
- LONG/SHORT各10件以上または不足を明記して不合格
- 2025/2026両sourceでexpectancy >= 0

### stacked portfolio

- OOF accepted 100件以上
- 月間中央値6件以上
- win rate >= 60%
- cost5 expectancy >= 2.5 USD/oz
- cost5 PF >= 1.25
- LONG/SHORT各30件以上
- 2025/2026両sourceでプラス
- 上位5trade利益依存 <= 50%
- max drawdown <= gross profit
- prefix/streaming parity 100%

## 解釈

このStageは研究開発用。2025/2026は既知期間であり、OOFで改善してもlive validationではない。次の未来paper期間で再確認する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
