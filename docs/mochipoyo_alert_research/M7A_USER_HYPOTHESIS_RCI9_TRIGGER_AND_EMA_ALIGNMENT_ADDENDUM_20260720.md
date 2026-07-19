# M7A User Hypothesis Addendum — RCI9 Trigger + EMA20/30/40 Alignment

作成日: 2026-07-20 JST

repo: `knitanr-a11y/xauusd-signal-lab`

branch: `feature/mochipoyo-alert-research`

## User hypothesis

ユーザーの実観察に基づく中心仮説は次のとおり。

```text
RCI9の局所反転が発火トリガー
+
EMA20 / EMA30 / EMA40が通知方向へ順番に並んでいることが方向許可条件
```

方向配列の定義:

```text
PRIMARY LONG
EMA20 > EMA30 > EMA40

PRIMARY SHORT
EMA20 < EMA30 < EMA40
```

## M7A evidence consistent with the hypothesis

M7A combined scopeでは:

```text
PRIMARY LONG
- rci9_turn_up: 8 / 9
- bullish EMA stack: 8 / 9
- rci9_turn_up AND bullish EMA stack: 7 / 9 genuine events
- same pair matched only 2 no-event controls

PRIMARY SHORT
- rci9_turn_down: 10 / 10
- bearish EMA stack: 10 / 10 observed primary SHORT events
```

XAUUSD scopeでは:

```text
PRIMARY LONG
- bullish EMA stack: 6 / 6

PRIMARY SHORT
- observed event rows are bearish EMA stack
- exact false-positive reduction from combining EMA stack with rci9_turn_down must be audited in M7B
```

これは、RCI9がタイミングを決め、EMA20/30/40配列が方向を許可する二段構造と整合する。

## Important distinction

現時点で確定と呼べるのは、ユーザー観察と短期データが強く一致していることまで。

まだ次を断定しない。

- EMA配列が内部実装上の必須条件である
- EMAの順番だけで十分である
- EMAの傾き、密集度、価格位置が不要である
- EXITや再通知にも同じEMA条件が使われる
- M15以外でも同じ数値設定・条件がそのまま成立する

## M7B priority correction

M7BではPRIMARYの最優先frozen candidatesを次の2層にする。

```text
KERNEL-L1
state == IDLE
AND rci9_turn_up
AND EMA20 > EMA30 > EMA40

KERNEL-S1
state == IDLE
AND rci9_turn_down
AND EMA20 < EMA30 < EMA40
```

同時に比較対象としてRCI9単独も残す。

```text
CORE-L0: state == IDLE AND rci9_turn_up
CORE-S0: state == IDLE AND rci9_turn_down
```

M7Bで比較するもの:

1. RCI9単独の再現率・誤検出
2. RCI9 + EMA方向配列の再現率・誤検出
3. EMA配列が崩れた本物イベントの個別確認
4. EMA配列だけ成立してRCI9反転がないno-event足
5. EMAの順番だけでなく、傾き・密集度・価格位置が追加条件か
6. BTCUSDとXAUUSDで同じ構造が維持されるか

## Guardrails

- trade outcome, MFE, MAE, win/lossを発火条件選択に使わない
- alert-bar high/low/closeを使わない
- closed M15 information only
- exact proprietary formulaと主張しない
- historical full scan、cross-timeframe extraction、entry gate、Discord、orderは未承認
- reentryはサンプル不足のため同じ条件を仮定しない
