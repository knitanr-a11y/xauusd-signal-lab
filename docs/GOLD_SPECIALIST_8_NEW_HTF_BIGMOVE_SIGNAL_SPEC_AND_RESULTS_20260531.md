# GOLD specialist 8 revised wide HTF big-move exploration

作成日: 2026-05-31

## 修正理由

前回の `TP10/SL5` / `TP15/SL7.5` は、上位足の数百pips級伸びを取る設計ではなく、下髭で狩られやすいスキャル寄りだったため却下。
今回は確定済みH1/H4/D1だけを使い、TP/SLを広げ、同一strategyの重複ポジションを禁止して再探索した。

## source of truth

アップロードされたOHLC:

```text
goldsharp_m15.csv
goldsharp_m5.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

## 未確定上位足禁止ルール

M15 signal_time に対して、H1/H4/D1は `close_time <= signal_time` の足だけを `merge_asof` で結合した。
open中のH1/H4/D1足は使っていない。

ledger監査結果:

```text
HTF confirmed violations = 0
```

## 勝敗判定

```text
entry_time: 次のM15足open
outcome timeframe: M5
same M5 bar TP/SL both hit: SL priority
同一strategy重複: 禁止。前回trade exit_time + 240分 まで次を出さない
AI API calls: 0
MT5 sends: 0
Discord sends: 0
```

## 候補1

```text
NEW_BUY_CONFIRMED_D1H4_BIGMOVE_M15_EMA50_PULLBACK_TP100_SL50_CAP4320_NO_OVERLAP
```

条件:

```text
D1 close > D1 EMA20
D1 EMA20 > D1 EMA50
D1 3本close変化 >= +80 USD または D1 5本range >= +112 USD
H4 close > H4 EMA20
H4 EMA20 > H4 EMA50
H4 ADX14 >= 18
H4 6本close変化 >= +80 USD または H4 12本range >= +120 USD
M15 low <= M15 EMA50
M15 close > M15 EMA20
M15 bullish candle
```

TP/SL:

```text
TP +100 USD
SL -50 USD
CAP 4320分
```

結果:

```text
expected_trades 31
WR 58.06%
PF 2.24
net +749.26 USD
recent90: 3件 / 0勝3敗 / -150 USD
```

注意: 全期間では良いが、直近90日は全敗。即live採用不可。追加候補として保留監査が必要。

## 候補2

```text
NEW_SELL_CONFIRMED_H4H1_BIGDOWN_D1BELOW_M15_EMA20_REJECT_TP80_SL40_CAP2880_NO_OVERLAP
```

条件:

```text
D1 close < D1 EMA20
H4 close < H4 EMA20
H4 EMA20 < H4 EMA50
H4 6本close変化 <= -100 USD または H4 12本range >= +150 USD
H1 close < H1 EMA20
H1 EMA20 < H1 EMA50
H1 ADX14 >= 20
H1 8本close変化 <= -20 USD
M15 high >= M15 EMA20
M15 close < M15 EMA20
M15 bearish candle
```

TP/SL:

```text
TP +80 USD
SL -40 USD
CAP 2880分
```

結果:

```text
expected_trades 19
WR 47.37%
PF 1.29
net +117.71 USD
recent90: 16件 / WR 50.00% / PF 1.37 / net +117.71 USD
```

注意: 直近は比較的良いが、PFは強くない。採用候補ではなく監視候補。

## 結論

前回の狭いSL候補は破棄。
広いSL/TPかつ確定済み上位足限定では、強く採用できる追加シグナルはまだない。
候補として残すなら上記2本。ただし、候補1は直近90日が悪く、候補2はPFが弱い。

## 次にやること

```text
1. 既存selected_8とのentry_time重複監査
2. 新2本だけを別ledgerでaudit-only
3. group aggregationに混ぜる前に、直近90日と2026年だけで再評価
4. AI APIはまだ呼ばない
```
