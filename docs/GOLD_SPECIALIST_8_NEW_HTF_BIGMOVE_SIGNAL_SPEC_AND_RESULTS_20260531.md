# GOLD specialist 8 新HTF big-moveシグナル探索仕様・結果

作成日: 2026-05-31
対象: GOLD / H1以上の大伸び / M15落とし込み / M5勝敗判定

## 1. 実装名

`GOLD specialist 8 new HTF big-move signal exploration`

## 2. 目的

H1以上で数十USD以上伸びている局面を、M15へ落として押し目・再上昇で拾える追加シグナルを探す。

今回の探索はAI評価ではない。OpenAI APIは呼ばない。

## 3. 入力CSV

今回の検証では、ユーザーがアップロードした以下のOHLCをsource of truthとして使用した。

```text
goldsharp_m15.csv
goldsharp_m5.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

## 4. 出力

ローカル検証で作成した出力:

```text
gold_specialist_8_new_htf_bigmove_signal_summary_20260531.csv
gold_specialist_8_new_htf_bigmove_source_trade_ledger_20260531.csv
gold_specialist_8_new_htf_bigmove_period_audit_20260531.csv
gold_specialist_8_new_htf_bigmove_rejected_sell_audit_20260531.csv
```

## 5. 共通判定仕様

```text
signal timeframe: M15
entry_time: 次のM15足open
entry_price: 次のM15足open
outcome timeframe: M5
outcome rule: M5先触れ判定
same M5 bar TP/SL both touched: SL priority
cooldown: strategy_id + direction 単位で60分
AI API calls: 0
MT5 order sends: 0
Discord sends: 0
```

## 6. 追加候補1

### strategy_id

```text
NEW_BUY_H4_DONCH36_BREAK_M15_EMA20_REJECT_TP10_SL5_CAP220
```

### direction

```text
BUY only
```

### 条件

```text
D1 close > D1 EMA20
H4 close > previous H4 Donchian36 high
H4 close > H4 EMA20
H4 ADX14 >= 15
H4 3本close変化 >= +40 USD
M15 low <= M15 EMA20
M15 close > M15 EMA20
M15 bullish candle
```

### TP/SL

```text
TP: +10 USD
SL: -5 USD
CAP: 220分
```

### 結果

```text
expected_trades: 53
wins: 30
losses: 23
win_rate: 56.60%
PF: 2.58
net: +178.74 USD
avg: +3.37 USD/trade
```

### 期間別

```text
2025: 37件 / WR 59.46% / PF 2.90 / net +138.74 USD
2026: 16件 / WR 50.00% / PF 2.00 / net +40.00 USD
直近90日: 6件 / WR 50.00% / PF 2.00 / net +15.00 USD
```

## 7. 追加候補2

### strategy_id

```text
NEW_BUY_H4H1_IMPULSE_M15_EMA20_RSI50_RECLAIM_TP15_SL75_CAP240
```

### direction

```text
BUY only
```

### 条件

```text
H4 close > H4 EMA20
H4 EMA20 > H4 EMA50
H4 6本close変化 >= +60 USD または H4 6本range >= +72 USD
H1 close > H1 EMA20
H1 EMA20 > H1 EMA50
H1 ADX14 >= 20
H1 8本close変化 >= +20 USD
M15 low <= M15 EMA20
M15 close > M15 EMA20
M15 bullish candle
M15 RSI14 crosses above 50
```

### TP/SL

```text
TP: +15 USD
SL: -7.5 USD
CAP: 240分
```

### 結果

```text
expected_trades: 27
wins: 16
losses: 11
win_rate: 59.26%
PF: 2.91
net: +157.50 USD
avg: +5.83 USD/trade
```

### 期間別

```text
2025: 10件 / WR 60.00% / PF 3.00 / net +60.00 USD
2026: 17件 / WR 58.82% / PF 2.86 / net +97.50 USD
直近90日: 9件 / WR 44.44% / PF 1.60 / net +22.50 USD
```

## 8. 採用しない条件

SELL対称形も検証したが、成績が弱い。

```text
NEW_SELL_H4_DONCH36_BREAK_M15_EMA20_REJECT_TP10_SL5_CAP220
21件 / WR 38.10% / PF 1.23 / net +15.00 USD

NEW_SELL_H4H1_IMPULSE_M15_EMA20_RSI50_RECLAIM_TP15_SL75_CAP240
23件 / WR 30.43% / PF 0.88 / net -15.00 USD
```

そのため、今回追加候補はBUY専用2本とする。

## 9. 成功条件

```text
entry_time / direction / tp / sl / outcome がsource trade ledgerに出ている
expected_tradesがsummaryとledgerで一致する
AI API callsが0
SELL対称形を混ぜない
```

## 10. 停止条件

```text
M5勝敗判定が作れない
entry_timeが欠ける
TP/SLが欠ける
BUY以外を混ぜる
AI APIを呼ぶ処理が混入する
```

## 11. 次にやること

この2本は、いきなりAI評価やlive導線へ入れない。

次の順序で進める。

```text
1. 新2本だけのsource trade ledgerを保存
2. 既存selected_8との重複時刻を監査
3. group aggregation仕様に追加するか判断
4. audit-only通過後に初めてAI評価対象候補にする
```
