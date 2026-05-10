# GOLD_FIRST_SCOPE_AND_SIGNAL_INVENTORY

## 目的

このドキュメントは、現在の作業範囲を **GOLD優先** に戻し、既存もちぽよ minimal と新GOLD multi-strategy の中身・違い・未統合点を整理するための棚卸しメモ。

ユーザー方針:

```text
BTCは後回し。
まずGOLDを完成させる。
BTCはGOLDが終わった後で別枠BATとして作る。
GOLDとBTCを無理に1つへ混ぜない。
.batで別々に作れば同時起動できる可能性がある。
同時起動に都合が悪ければ、後でまとめ方を検討する。
```

---

## 現在確認できている実運用入口

GOLD demo autotrade 実運用入口:

```text
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
```

このBATはGOLD専用。

主な指定:

```text
--symbol GOLD
--order-broker-symbol GOLD#
--enable-auto-trade-send
--auto-trade-broker-symbol GOLD#
--auto-trade-position-policy block_any
--auto-trade-max-symbol-positions 1
--auto-trade-max-symbol-lot 0.01
--commit-trigger-state
--commit-ledger
--discord-send
```

したがって、このBAT単体ではBTCシグナル通知・BTC注文は動いていない。

---

## 既存もちぽよ minimal の構成

設定ファイル:

```text
scripts/mochipoyo_minimal_config.py
```

この設定ファイルにはGOLDとBTCのpair定義が両方ある。

ただし、実運用BATが `--symbol GOLD` で起動しているため、現在のGOLD実運用BATではGOLDだけが対象。

### 既存GOLD pair

```text
GOLD_H4_M5_SCALP
GOLD_H4_M15_DAYTRADE
GOLD_D1_H1_DAYTRADE
```

### BTC pair 定義

```text
BTC_H4_M15_DAYTRADE
```

BTCは設定上は存在するが、今回のGOLD完成作業では後回し。

---

## 既存もちぽよ minimal scanner の基本構造

関連ファイル:

```text
scripts/run_mochipoyo_gold_minimal_live_once.py
scripts/run_mochipoyo_gold_minimal_live_loop_aligned.py
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py
scripts/mochipoyo_minimal_scanner.py
scripts/mochipoyo_candidate_generators.py
```

基本流れ:

```text
pair trigger state
  -> should_scan=True のpairだけ読む
  -> confirmed-time join
  -> audited Mochipoyo scoring function でcandidate state生成
  -> event filter
  -> risk enrich
  -> notification eligibility
  -> trigger window filter
  -> notification ledger duplicate filter
  -> Discord送信またはdry-run
  -> order payload生成
  -> MT5 sender auto-trade stage
```

`mochipoyo_candidate_generators.py` の現行scope:

```text
GOLD_H4_M5_SCALP
GOLD_H4_M15_DAYTRADE
GOLD_D1_H1_DAYTRADE
BTC_H4_M15_DAYTRADE
```

generatorは `scan_mochipoyo_multi_tf_candidates.py` の既存audited indicator/scoring関数を再利用し、event filterは以下のdefaultを使う。

```text
min_rank = B
require_any_divergence = true
require_granville = true
cooldown_minutes_default = 240
max_per_day_per_pair_direction = 6
```

---

## 既存もちぽよGOLDの中身

### GOLD_H4_M5_SCALP

設定:

```text
symbol: GOLD
mt5_symbol: GOLD#
base_timeframe: M5
trigger_timeframe: M5
context: H4
allowed_slices:
  candidate_rank A / SELL
  candidate_rank B / SELL
```

意味:

```text
H4文脈 + M5ベースのGOLD短期SELL系scalp候補。
A/B rank のSELLだけが通知対象。
```

### GOLD_H4_M15_DAYTRADE

設定:

```text
symbol: GOLD
mt5_symbol: GOLD#
base_timeframe: M15
trigger_timeframe: M15
context: H4
allowed_slices:
  candidate_rank B / BUY
  candidate_rank B / SELL
```

意味:

```text
H4文脈 + M15ベースのGOLD daytrade候補。
B rank のBUY/SELLが対象。
```

### GOLD_D1_H1_DAYTRADE

設定:

```text
symbol: GOLD
mt5_symbol: GOLD#
base_timeframe: H1
trigger_timeframe: H1
context: D1
allowed_slices:
  candidate_rank A / BUY
  candidate_rank B / BUY
```

意味:

```text
D1文脈 + H1ベースのGOLD daytrade BUY候補。
A/B rank のBUYが対象。
```

---

## 既存もちぽよと新GOLD multi-strategyの違い

既存もちぽよ:

```text
既存audited Mochipoyo scoring function由来。
GOLD_H4_M5_SCALP / GOLD_H4_M15_DAYTRADE / GOLD_D1_H1_DAYTRADE。
trigger-state / notification-ledger / Discord / auto-trade stage を持つ。
現行GOLD実運用BATではGOLD#へdemo auto-trade可能。
```

新GOLD multi-strategy:

```text
既存もちぽよ本体とは別に作ってきた追加GOLD戦略群。
BUY_C_ENV_RR2_72H と SELL_H1H4_BEAR_AB をrouterで束ねる。
sidecar dry-run / guarded demo send flowとして検証中。
既存もちぽよ実運用BATにはまだ統合していない。
```

---

## 新GOLD multi-strategy 現在の戦略スロット

### BUY_C_ENV_RR2_72H

strategy:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

概要:

```text
H4 C_ENV:
  最新確定H4で ema20 > ema50 かつ close > ema50

H1 regular bullish divergence:
  価格は安値更新、MACDは切り上げ

M15 break:
  M15で上方向ブレイク確認

RR:
  RR2

holding:
  72H系の管理
```

位置づけ:

```text
GOLDのBUY追加戦略。
既存もちぽよGOLD BUYとは別根拠。
```

### SELL_H1H4_BEAR_AB

strategy:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

rank仕様:

```text
CORE_AB_CONFIRM = A and B
  trade_enabled = true
  lot_multiplier = 2.0

B_ONLY_SAFE = B and not A
  trade_enabled = true
  lot_multiplier = 1.0

A_ONLY_OBSERVE = A and not B
  trade_enabled = false
  lot_multiplier = 0.0
```

A condition summary:

```text
H1:
  close < EMA20
  EMA20 < EMA50
  EMA20 slope3 < 0
  (EMA20 - close) / ATR14 <= 1.60

H4:
  close < EMA20
  EMA20 < EMA50

D1:
  close < EMA20

M15:
  low < previous rolling low 16
  close_pos <= 0.45
  MACD hist delta < 0
  range / ATR14 >= 0.90
```

B condition summary:

```text
H1:
  close < EMA50
  EMA20 < EMA50
  (EMA20 - close) / ATR14 <= 1.60

H4:
  EMA20 < EMA50

D1:
  close < EMA20

M15:
  low < previous rolling low 6
  close_pos <= 0.50
  MACD hist < 0
  MACD hist delta < 0
```

lot解釈:

```text
base_lot 0.01 の場合:
  CORE_AB_CONFIRM -> 0.02
  B_ONLY_SAFE     -> 0.01
  A_ONLY_OBSERVE  -> 注文しない
```

位置づけ:

```text
GOLDのH1/H4 bearish文脈 + M15 low break系SELL追加戦略。
既存もちぽよGOLD SELLとは別根拠。
```

---

## 複数ポジション/逆方向ポジションの方針

ユーザー方針:

```text
別シグナルなら複数ポジションOK。
H1下落SELLの途中でも、もちぽよBUYなどが上昇調整を取れるなら止めない。
BUY/SELLが同時に存在しても、別ロジック・別時間軸なら許容。
```

したがって、統合時にやってはいけないこと:

```text
GOLDに既存ポジションがあるだけで新シグナルを止める。
SELL系シグナル中だからBUYを止める。
BUY系シグナル中だからSELLを止める。
銘柄単位の block_any / max 1 position を新multi-strategy全体へ強制する。
```

止めるべきもの:

```text
同じorder_keyの再送。
同じsignal_keyの再送。
同じstrategy_id + confirmed_m15_time の重複。
同じ戦略スロットで同じ足に何度も出る重複。
```

止めないもの:

```text
別strategy_idの別シグナル。
別signal_keyの別シグナル。
逆方向でも別根拠のシグナル。
```

---

## GOLD完成のための次作業

BTCは後回し。

GOLDを先に完成させるため、次はコードを触る前に以下を確認する。

```text
1. build_mochipoyo_order_payloads.py
   既存もちぽよ order_key / payload_key / lot仕様

2. send_mt5_order_from_payload.py
   order ledger重複判定キー
   position-policyがどこまで銘柄単位か
   payload lotを尊重するか

3. GOLD multi-strategy側の order_intent/payload変換
   lot_multiplier / effective_lot / strategy_id / signal_key がpayloadへ渡るか

4. run_mochipoyo_gold_minimal_live_loop_aligned.py へのhook設計
   既存もちぽよGOLD実運用を壊さず、新GOLD multi-strategyを同一GOLD側ループに入れる方法
```

---

## 今後の統合仕様メモ

GOLD統合で目指す形:

```text
既存もちぽよGOLD:
  現行実運用を壊さない。

新GOLD multi-strategy:
  GOLD側へ追加。
  別シグナルなら複数ポジションOK。
  H1下落SELL中のBUY調整取りを止めない。
  A+Bなら0.02、B_ONLYなら0.01を守る。
  同じシグナル重複だけ止める。
```

BTC:

```text
GOLD完成後に別枠BATとして作る。
同時起動する場合は、GOLD/BTCそれぞれout-dir / ledger / trigger-state / order-ledger / lockを分離する。
必要なら後で親BATを作る。
```

---

## 現時点の結論

```text
作業範囲はGOLD優先に戻す。
BTCは後回し。
既存もちぽよGOLDと新GOLD multi-strategyの中身は別物。
統合時は銘柄単位blockではなく、strategy/signal/order key単位の重複防止を使う。
```
