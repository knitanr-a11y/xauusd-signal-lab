# GOLD H4 Divergence Pullback -> M15/M5 Re-entry Design

最終更新: 2026-05-07

このドキュメントは、GOLD/XAUUSD の H4 ダイバージェンス押し目を、下位足へ落としてプログラム化しやすいトレードポイントとして整理するための設計メモである。

対象ケース:

```text
GOLD H4 2026-05-04 20:00 の足付近で、ダイバージェンス発生後に上昇。
押し目として機能しているように見える。
こういう場所を積極的に取りたい。
```

MACD設定はユーザー指定を使う。

```text
Fast EMA = 6
Slow EMA = 13
Signal = 4
```

---

## 1. 基本方針

H4ダイバージェンス足そのものでエントリーしない。
H4は方向フィルター・環境認識として扱い、下位足で「買いが勝ち始めた証拠」を待つ。

```text
H4 = 買いだけ探してよい場所かを判定
M15 = 反転確認
M5 = エントリー
```

狙いたい構造:

```text
H4上昇環境
  -> 一度下げて押し目形成
  -> H4 MACD ダイバージェンス
  -> 下落失敗
  -> M15で反転確認
  -> M5で最初の押し戻しを買う
```

---

## 2. MACD定義

全時間足で同じ設定を使う。

```text
macd_line = EMA(close, 6) - EMA(close, 13)
signal    = EMA(macd_line, 4)
hist      = macd_line - signal
```

使う列候補:

```text
macd_line_h4
macd_signal_h4
macd_hist_h4
macd_line_m15
macd_signal_m15
macd_hist_m15
macd_line_m5
macd_signal_m5
macd_hist_m5
```

---

## 3. H4ダイバージェンスの扱い

### 3.1 本命: H4 Hidden Bullish Divergence

押し目継続を狙うなら、優先したいのはヒドゥン強気ダイバージェンス。

定義:

```text
価格:
  H4の押し安値が前回押し安値より高い
  price_low_2 > price_low_1

MACD:
  MACDの谷が前回より低い
  macd_low_2 < macd_low_1

意味:
  価格はそこまで下げていないのに、MACDだけ深く下げた。
  上昇トレンド中の押し目継続候補。
```

### 3.2 通常の強気ダイバージェンス

反転候補として使う。

定義:

```text
価格:
  price_low_2 < price_low_1

MACD:
  macd_low_2 > macd_low_1

意味:
  安値更新したが、MACDの下落圧力は弱くなっている。
  下落失敗からの反転候補。
```

今回の目的は「押し目として機能する場所を積極的に取る」ことなので、まずは hidden bullish divergence を本命にする。

---

## 4. 下位足のエントリーパターン

### Pattern A: M15戻り高値ブレイク

もっともシンプルでプログラム化しやすい。

条件:

```text
H4_CONTEXT_BUY = True
M15 close > 直近戻り高値
M15 macd_line > macd_signal
M15 macd_hist > macd_hist[1]
M15 close > ema20
```

エントリー:

```text
M15戻り高値ブレイク足確定
または
その後のM5押し目
```

メリット:

```text
構造転換後なので騙しが少なめ。
コード化しやすい。
```

デメリット:

```text
やや遅い。
```

---

### Pattern B: M15反転後のM5初回押し目

今回の目的に一番合う本命パターン。

流れ:

```text
H4で押し目ダイバージェンス
  -> M15で戻り高値ブレイク
  -> M5でEMA20付近まで押す
  -> M5 MACDが再加速
  -> M5の小さな戻り高値を抜けたらBUY
```

M5買い条件:

```text
M15_buy_context = True
low_m5 <= ema20_m5 + atr14_m5 * 0.2
close_m5 > ema20_m5
M5安値切り上げ
macd_hist_m5 > macd_hist_m5[1]
macd_line_m5 > macd_signal_m5
close_m5 > 直近M5小高値
```

メリット:

```text
H4の大きな押し目を、M5でリスク小さく拾える。
下位足で買い直しが確認できる。
```

---

### Pattern C: M5通常ダイバージェンス早入り

早く入る版。

条件:

```text
H4_CONTEXT_BUY = True
M15下落勢いが弱い
M5 regular bullish divergence = True
M5 macd_hist > macd_hist[1]
M5 close > 直近M5小高値
```

M5 regular bullish divergence:

```text
price_low_2 < price_low_1
macd_low_2 > macd_low_1
```

メリット:

```text
安く拾える。
SLを近く置きやすい。
```

デメリット:

```text
逆張り気味。
M5ノイズが多い。
単体では騙しが増える。
```

---

## 5. 最初に検証する本命ルール

名前候補:

```text
GOLD_H4_DIV_PULLBACK_M15_M5_REENTRY
```

または、もちぽよ式の名前候補:

```text
GOLD_H4_M15_M5_DIV押し目再加速
```

### 5.1 H4_CONTEXT_BUY

```text
ema20_h4 > ema50_h4
close_h4 > ema50_h4
hidden_bullish_div_h4 == True
```

補助条件候補:

```text
close_h4 >= ema20_h4 - atr14_h4 * 0.5
macd_hist_h4 is improving after divergence
```

### 5.2 M15_TRIGGER_BUY

```text
close_m15 > rolling_high_m15_lookback_8_prev
macd_line_m15 > macd_signal_m15
macd_hist_m15 > macd_hist_m15[1]
close_m15 > ema20_m15
```

### 5.3 M5_ENTRY_BUY

```text
low_m5 <= ema20_m5 + atr14_m5 * 0.2
close_m5 > ema20_m5
macd_hist_m5 > macd_hist_m5[1]
macd_line_m5 > macd_signal_m5
close_m5 > rolling_high_m5_lookback_6_prev
```

### 5.4 Entry

```text
BUY at M5 close after M5_ENTRY_BUY confirmed
```

### 5.5 SL候補

```text
SL = M5押し目直近安値下
または
SL = M15反転前安値下
```

### 5.6 TP候補

```text
TP1 = 直近H4高値
TP2 = RR 1.2〜1.5
または
M15 macd_hist 減速 + M15 close < ema20_m15
```

---

## 6. Pivot / Swing定義

主観を減らすため、まずは pivot/fractal 方式でスイングを定義する。

```text
pivot_low:
  low[i] が前後2本のlowより低い

pivot_high:
  high[i] が前後2本のhighより高い
```

注意:

```text
右側2本を待つため、pivot確定は2本遅れる。
M5なら約10分遅れで許容しやすい。
M15なら約30分遅れでやや遅い。
```

そのため、初期設計では以下がよい。

```text
H4 / M15 の構造判定:
  pivot方式

M5 のエントリー:
  rolling high breakout / EMA20 retest / MACD再加速
```

---

## 7. バックテスト時の優先順位

まずは以下の順で検証する。

```text
第1候補:
  H4 hidden bullish divergence
  + M15戻り高値ブレイク
  + M5 EMA20押し目再加速

第2候補:
  H4 bullish divergence
  + M15 MACD cross
  + M5 EMA20 bounce

第3候補:
  H4 divergence
  + M5 regular bullish divergence early entry
```

---

## 8. 重要な設計思想

H4ダイバージェンスは「すぐ買うサイン」ではなく、買いだけを探してよい環境として扱う。

```text
H4のダイバージェンス:
  下落が弱まった可能性

下位足の反転確認:
  実際に買いが勝ち始めた証拠
```

よって、実装は必ず以下に分ける。

```text
H4 = context filter
M15 = trigger confirmation
M5 = entry execution
```

---

## 9. 新チャットでやること

新チャットでは、まずこの設計をもとに以下を進める。

```text
1. 現在のCSV列・既存indicator関数の確認
2. MACD 6/13/4 の列追加または既存列の再利用確認
3. H4 pivot low / hidden bullish divergence 検出実装
4. M15戻り高値ブレイク検出
5. M5 EMA20 retest + MACD再加速 + 小高値ブレイク検出
6. 2026-05-04 20:00 H4 付近のケーススタディCSV出力
7. その後に期間を広げてバックテスト
```
