# NEXT CHAT HANDOFF - GOLD H4 DIV PULLBACK REENTRY

最終更新: 2026-05-07

次チャットでは、GOLD/XAUUSD の H4ダイバージェンス押し目を下位足で取る新しい検証ルールを組み上げる。

最初に読むドキュメント:

```text
docs/GOLD_H4_DIV_PULLBACK_M15_M5_REENTRY_DESIGN.md
```

---

## ユーザーが取りたい形

ユーザーは、GOLDの4時間足で 2026-05-04 20:00 の足付近に出たダイバージェンス後の上昇を見て、以下のような場所を積極的に取りたい。

```text
H4でダイバージェンス発生
押し目として機能
その後に上昇
```

これを、下位足に落としてプログラム化しやすい形にしたい。

MACD設定はユーザー指定を使う。

```text
MACD Fast EMA = 6
MACD Slow EMA = 13
Signal = 4
```

---

## 重要な設計方針

H4ダイバージェンス足で即エントリーしない。

```text
H4 = 買いだけ探してよい環境かを見る
M15 = 反転確認
M5 = 実際のエントリー
```

H4ダイバージェンスは「下落が弱まった可能性」であり、エントリー根拠は下位足で買いが勝ち始めた証拠にする。

---

## 最初に作る本命ルール

名前候補:

```text
GOLD_H4_DIV_PULLBACK_M15_M5_REENTRY
```

または:

```text
GOLD_H4_M15_M5_DIV押し目再加速
```

基本構造:

```text
H4 hidden bullish divergence
  + M15戻り高値ブレイク
  + M5 EMA20押し目再加速
```

---

## 条件案

### H4_CONTEXT_BUY

```text
ema20_h4 > ema50_h4
close_h4 > ema50_h4
hidden_bullish_div_h4 == True
```

Hidden bullish divergence:

```text
価格:
  H4の押し安値が前回押し安値より高い
  price_low_2 > price_low_1

MACD:
  MACDの谷が前回より低い
  macd_low_2 < macd_low_1
```

通常の強気ダイバージェンスも第2候補として使う。

```text
price_low_2 < price_low_1
macd_low_2 > macd_low_1
```

### M15_TRIGGER_BUY

```text
close_m15 > rolling_high_m15_lookback_8_prev
macd_line_m15 > macd_signal_m15
macd_hist_m15 > macd_hist_m15[1]
close_m15 > ema20_m15
```

### M5_ENTRY_BUY

```text
low_m5 <= ema20_m5 + atr14_m5 * 0.2
close_m5 > ema20_m5
macd_hist_m5 > macd_hist_m5[1]
macd_line_m5 > macd_signal_m5
close_m5 > rolling_high_m5_lookback_6_prev
```

Entry:

```text
BUY at M5 close after M5_ENTRY_BUY confirmed
```

SL:

```text
M5押し目直近安値下
または
M15反転前安値下
```

TP:

```text
直近H4高値
または
RR 1.2〜1.5
```

---

## 実装方針

スイング判定はまず pivot/fractal 方式でよい。

```text
pivot_low:
  low[i] が前後2本のlowより低い

pivot_high:
  high[i] が前後2本のhighより高い
```

ただし、M5エントリーはpivot確定を待ちすぎると遅くなるため、まずは以下でよい。

```text
H4 / M15:
  pivot方式で構造判定

M5:
  rolling high breakout
  EMA20 retest
  MACD再加速
```

---

## 新チャットで最初にやること

```text
1. 現在のCSV列・既存indicator関数の確認
2. MACD 6/13/4 の列追加または既存列の再利用確認
3. H4 pivot low / hidden bullish divergence 検出実装
4. M15戻り高値ブレイク検出
5. M5 EMA20 retest + MACD再加速 + 小高値ブレイク検出
6. 2026-05-04 20:00 H4 付近のケーススタディCSV出力
7. その後に期間を広げてバックテスト
```

---

## 現チャットで続けること

現チャットでは、新ルール実装ではなく、もちぽよ式 GOLD minimal live loop / bat 停止原因の調査を続ける。

現在の停止調査で重要なこと:

```text
run_mochipoyo_gold_demo_autotrade_forever_aligned.bat を使う予定。
ただし、loopがまた止まったため、該当iterationの once_stderr.txt / once_stdout.txt / minimal_live_once_summary.csv を確認する。
```

見るべき例:

```cmd
type data\ml_loop_demo_prod_forever\iter_xxxx\once_stderr.txt
type data\ml_loop_demo_prod_forever\iter_xxxx\once_stdout.txt
python -c "import pandas as pd; p=r'data\ml_loop_demo_prod_forever\iter_xxxx\minimal_live_once_summary.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); print(df.to_string(index=False))"
```
