# GOLD V3 Stage264 定義固定
## H1エントリー / H4比較 / D1-H4環境認識 中期自動売買監査

作成日: 2026-06-21  
状態: `GOLD_V3_264_H1_ENTRY_H4_D1_MEDIUM_TERM_AUTOTRADE_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

M15方向予測を停止し、D1・H4の中期方向を使ってH1またはH4で自動エントリーする設計へ切り替える。

本Stageは、短期ノイズと取引コストの影響を減らしつつ、最近の上昇相場だけに依存しない中期edgeがあるかを監査する。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- 2025年・2026年の既知結果を使ってparameterを変更しない。
- 本定義の2戦略以外を追加探索しない。
- LONGのみ、SHORTのみ、年別filter、結果後の時間帯filterを行わない。
- 同一barでTPとSLへ触れた場合はSL優先。
- 近傍bar、次bar、前barへの価格fallbackをしない。
- candidateは削除せず、data不足・session不足を状態として記録する。
- MT5発注、通知、live hook、order payload、autotrade、final signalは禁止。

## データ可用性

- H1: 2023-01-25以降。
- H4: 2019-12-20以降。
- D1: 2007-03-23以降。
- M1: 2026-01-13以降。M1は2026年部分のpath/parity診断にのみ使う。

CSV `time`はbar OPEN時刻。

source availability:

- H1 source_close_time = time + 1時間。
- H4 source_close_time = time + 4時間。
- D1 source_close_time = time + 1日。
- decision_time以前にcloseしたsourceだけをas-of使用する。

## 共通indicator

各timeframeで因果計算する。

- EMA20
- EMA50
- ATR14: true rangeのWilder EMA
- ATR50: true rangeのWilder EMA

絶対価格thresholdは使用しない。

## 共通trend state

LONG環境:

- D1 EMA20 > EMA50
- H4 EMA20 > EMA50
- H4 close > H4 EMA20

SHORT環境:

- D1 EMA20 < EMA50
- H4 EMA20 < EMA50
- H4 close < H4 EMA20

不一致はNO TRADE。

# Strategy A: H1 pullback reclaim

本命戦略。

## signal bar

完了H1 barで判定する。

decision_time = signal H1 time + 1時間。

LONG:

1. 共通LONG環境。
2. signal H1 close > EMA20。
3. signal H1 close > signal H1 open。
4. signal H1 close > 直前2本のH1 high最大値。
5. signal barを含む直近3本のH1 low最小値 <= 各bar EMA20の最大値。

SHORTは完全反転:

1. 共通SHORT環境。
2. close < EMA20。
3. close < open。
4. close < 直前2本のlow最小値。
5. 直近3本のhigh最大値 >= 各bar EMA20の最小値。

## entry

- entry_time = decision_time。
- entry_price = entry_timeに始まるexact H1 OPEN。
- entry_timeのUTC hourは08:00以上14:00以下。
- 月曜〜金曜。
- one active position。

## risk / exit

signal時点H1 ATR14を固定する。

- LONG SL = entry - 1.0 ATR。
- LONG TP = entry + 2.0 ATR。
- SHORT SL = entry + 1.0 ATR。
- SHORT TP = entry - 2.0 ATR。
- 最大保有 = 6本のH1 bar。
- TP/SL未到達はentryから6時間後に始まるexact H1 OPENでTIME_EXIT。
- expected H1 sequenceが途中欠損した場合は`DATA_MISSING_BLOCKED`。
- 同一H1 TP+SLはSL優先。

# Strategy B: H4 aligned breakout

低頻度比較戦略。

## signal bar

完了H4 barで判定する。

decision_time = signal H4 time + 4時間。

LONG:

1. 共通LONG環境。
2. signal H4 close > signal H4 open。
3. signal H4 close > 直前6本のH4 high最大値。

SHORT:

1. 共通SHORT環境。
2. signal H4 close < signal H4 open。
3. signal H4 close < 直前6本のH4 low最小値。

## entry

- entry_time = decision_time。
- entry_price = entry_timeに始まるexact H4 OPEN。
- entry_timeのUTC hourは08:00または12:00のみ。
- 月曜〜金曜。
- one active position。

## risk / exit

signal時点H4 ATR14を固定する。

- SL = 1.25 ATR。
- TP = 2.5 ATR。
- 最大保有 = 2本のH4 bar、8時間。
- TP/SL未到達はentryから8時間後に始まるexact H4 OPENでTIME_EXIT。
- expected H4 sequence欠損は`DATA_MISSING_BLOCKED`。
- 同一H4 TP+SLはSL優先。

## cost

各resolved tradeについて:

- cost2 PnL = gross PnL - 2 USD。
- cost5 PnL = gross PnL - 5 USD。

swap実績は現在データにないため正式live収益には含めない。翌日跨ぎを避ける最大6時間・8時間設計とする。

## retrospective監査

### Strategy A

- 全H1 available period。
- year / half / month / direction別。
- 2023+2024合算と2025+2026合算を分離。

### Strategy B

- 2020年以降の全H4 period。
- year / half / month / direction別。
- pre-2025と2025+2026を分離。

## M1 path診断

2026-01-13以降について、entry/exitがM1範囲内にあるtradeはM1 pathでも再評価する。

- entryはexact M1 OPEN。
- TP/SLはM1 high/low。
- 同一M1はSL優先。
- H1/H4 bar判定とのexit_reason / PnL差を記録。
- M1結果を使ってstrategy parameterを変更しない。

## 合否基準

### Strategy A H1

全て必要:

1. resolved trade 100件以上。
2. coverage 98%以上。
3. 全期間cost2 expectancy > 0。
4. 全期間cost2 PF >= 1.15。
5. cost5 expectancy > 0。
6. 2023+2024合算cost2 PnL >= 0。
7. LONG・SHORT各30件以上。
8. LONG・SHORT各cost2 PnL >= 0。
9. positive gross profitの単一年依存 <= 70%。
10. max drawdown <= gross profit。
11. M1対象tradeで方向・entry parity 100%。

### Strategy B H4

全て必要:

1. resolved trade 80件以上。
2. coverage 98%以上。
3. 全期間cost2 expectancy > 0。
4. 全期間cost2 PF >= 1.15。
5. cost5 expectancy > 0。
6. 2020〜2024合算cost2 PnL >= 0。
7. LONG・SHORT各20件以上。
8. LONG・SHORT各cost2 PnL >= 0。
9. positive gross profitの単一年依存 <= 70%。
10. max drawdown <= gross profit。
11. M1対象tradeで方向・entry parity 100%。

## formal判定

- A合格、B不合格: `H1_MEDIUM_TERM_CANDIDATE_PROMISING_NOT_VALIDATED`
- B合格、A不合格: `H4_MEDIUM_TERM_CANDIDATE_PROMISING_NOT_VALIDATED`
- 両方合格: `H1_H4_MEDIUM_TERM_CANDIDATES_PROMISING_NOT_VALIDATED`
- 両方不合格: `H1_H4_MEDIUM_TERM_AUTOTRADE_REJECTED`
- coverage/parity不能: `H1_H4_MEDIUM_TERM_DATA_OR_PARITY_BLOCKED`

合格しても2025・2026は既知期間でありlive-readyではない。broker calendar、spread、swap、new future paper holdoutが必要。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
