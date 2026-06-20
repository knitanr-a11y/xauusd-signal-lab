# GOLD V3 Stage265 定義固定
## H1/H4 intrabar breakout entry audit-only

作成日: 2026-06-21  
状態: `GOLD_V3_265_HTF_INTRABAR_BREAKOUT_ENTRY_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

H1/H4をsetup・entry timeframeとして維持したまま、ブレイクを同時間足の終値確定まで待たず、事前固定した上位足水準へのM1到達でpending stop注文を約定させる。

M1は短期setup判断には使わず、事前注文の約定時刻・gap・TP/SL順序を再現するexecution resolutionとしてのみ使う。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- CSV各行は確定足、`time`はOPEN時刻。
- availabilityは M1=time+1分、H1=time+1時間、H4=time+4時間、D1=time+1日。
- source_close_time <= decision_time の情報だけを使用。
- 形成中H1/H4の最終OHLCをentry条件・水準計算に使わない。
- M1 high/lowを見てから同じM1 openへ遡ってentryしない。
- 水準・方向・ATR・SL・TP・注文期限は注文作成時に固定。
- future情報でcandidateを削除しない。
- 近傍barへのfallback禁止。
- 同一M1でentry後TP/SL両方に触れ得る場合はSL優先。
- LONG only、SHORT only、年別filter、結果後のparameter変更禁止。
- order送信・通知・live hookは禁止。

## データ区間

execution M1はsource区間を分けて保持する。

- `gold#_m1`: 2025-01-02〜2025-12-31、source_id=`GOLD_HASH_2025`
- `goldsharp_m1`: 2026-01-13〜2026-06-19、source_id=`GOLDSHARP_2026`

両M1 sourceの連続同一性は証明済みと扱わない。集計はsource別とcombined diagnosticを出す。live昇格には使用しない。

上位足は`goldsharp_h1/h4/d1`を使用する。2025重複区間でgold#とOHLC等が同一だった事実はあるが、broker identity証明にはしない。

## 共通indicator

確定済みbarだけで因果計算する。

- EMA20
- EMA50
- ATR14: Wilder EMA true range

## 共通context

LONG許可:

- 利用可能な最新D1 EMA20 > EMA50
- 利用可能な最新H4 EMA20 > EMA50
- 最新H4 close > EMA20

SHORT許可は完全反転。

不一致はcandidateを作らず、`NO_CONTEXT`として集計する。

# Strategy A: H1 intrabar pullback breakout

## 注文作成

各完了H1について:

- decision_time = H1 time + 1時間
- decision_time UTC hour 08〜14、平日
- 最新完了H1を含む直近3本を使用

LONG setup:

1. 共通LONG context
2. 最新H1 close > H1 EMA20
3. 直近3本low最小値 <= 直近3本EMA20最大値

SHORTは反転。

事前注文水準:

- LONG stop = 直近3本H1 high最大値
- SHORT stop = 直近3本H1 low最小値
- signal ATR = 最新完了H1 ATR14
- SL距離 = 1.0 ATR
- TP距離 = 2.0 ATR

注文有効期間:

- decision_timeから60分
- 次のH1 bar内部だけ
- 次のH1確定時に未約定注文は`EXPIRED`、新candidateは別setup_id

## 約定

その後のexact M1のみを順番に読む。

LONG:

- M1 open >= stopならgap fill=`M1 open`
- それ以外でM1 high >= stopならfill=`stop`

SHORT:

- M1 open <= stopならgap fill=`M1 open`
- それ以外でM1 low <= stopならfill=`stop`

fill前のM1 low/highでSL/TP判定をしない。

## exit

- entry後6時間までM1で監視
- LONG SL=fill-1ATR、TP=fill+2ATR
- SHORT SL=fill+1ATR、TP=fill-2ATR
- 同一M1でentryとSLへ触れ得る場合はSL
- 同一M1でTP/SL両方ならSL
- 未到達はentry_time+6時間のexact M1 OPENでTIME_EXIT
- 20:00 UTCを越えるtradeは`SESSION_WINDOW_BLOCKED`としてentryさせない

# Strategy B: H4 intrabar channel breakout

## 注文作成

各完了H4について:

- decision_time = H4 time + 4時間
- decision_time UTC hour 08または12、平日

LONG setup:

1. 共通LONG context
2. 最新完了H4 close > H4 EMA20

SHORTは反転。

事前注文水準:

- LONG stop = 直近6本完了H4 high最大値
- SHORT stop = 直近6本完了H4 low最小値
- ATR = 最新完了H4 ATR14
- SL距離 = 1.25 ATR
- TP距離 = 2.5 ATR

注文有効期間:

- decision_timeから4時間
- 次のH4 bar内部だけ
- 未約定はEXPIRED

## 約定とexit

- M1 gap/touch規則はH1と同じ
- entry後8時間までM1で監視
- 20:00 UTCを越えるtradeはentryさせない
- 同一M1はSL優先
- 未到達はentry_time+8時間のexact M1 OPENでTIME_EXIT

## one setup / one trade

- setup_idはstrategy + decision_time
- 各setupは最大1trade
- trade保有中は新candidateを`ONE_ACTIVE_SUPPRESSED`として残す
- pending注文同士は重ねず、先に作られた注文の有効期間中は後続を`PENDING_ORDER_SUPPRESSED`として残す

## cost

- cost2 PnL = gross - 2 USD
- cost5 PnL = gross - 5 USD

## 比較

Stage264の同時間足終値確認後entryと比較し、intrabar化で以下が改善したかを確認する。

- fill時点
- entry price
- SL/TP/TIME比率
- expectancy
- PF
- max drawdown

Stage264 parameterを結果後に変更しないため、exit倍率と最大保有はStage264と同じ。

## 合否基準

各strategyで全て必要:

1. resolved trades 30件以上
2. trigger coverage 98%以上
3. cost2 expectancy > 0
4. cost2 PF >= 1.15
5. cost5 expectancy > 0
6. LONG・SHORT各10件以上
7. LONG・SHORT各cost2 PnL >= 0
8. 2025 source区間と2026 source区間の両方でcost2 expectancy >= 0
9. max drawdown <= gross profit
10. gap fill率 <= 20%
11. batch/prefix/streaming candidate・注文・fill完全一致

## formal states

- `GOLD_V3_265_H1_INTRABAR_BREAKOUT_PROMISING_NOT_VALIDATED_AUDIT_ONLY`
- `GOLD_V3_265_H4_INTRABAR_BREAKOUT_PROMISING_NOT_VALIDATED_AUDIT_ONLY`
- `GOLD_V3_265_H1_H4_INTRABAR_BREAKOUT_PROMISING_NOT_VALIDATED_AUDIT_ONLY`
- `GOLD_V3_265_HTF_INTRABAR_BREAKOUT_REJECTED_AUDIT_ONLY`
- `GOLD_V3_265_DATA_OR_PARITY_BLOCKED_AUDIT_ONLY`

合格してもsource identity・calendar・spread path・future holdout不足のためlive-readyではない。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
