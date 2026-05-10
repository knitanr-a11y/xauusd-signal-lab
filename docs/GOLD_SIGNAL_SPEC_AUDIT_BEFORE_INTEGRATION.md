# GOLD_SIGNAL_SPEC_AUDIT_BEFORE_INTEGRATION

## 目的

GOLD統合前に、既存もちぽよGOLDと新GOLD multi-strategyのシグナル仕様が、決定時の仕様と現在のコード・棚卸しdocで相違ないか確認する。

結論:

```text
BUY_C_ENV_RR2_72H:
  条件仕様は概ね一致。
  ただし統合時に保持すべき重要条件が棚卸しdocだけでは薄い。
  統合時のpayload lotは base_lot 0.01 等で明示する必要がある。

SELL_H1H4_BEAR_AB:
  条件仕様・rank仕様は一致。
  base_lot default 0.10 問題は修正済み。
  現在は base_lot 0.01 に統一済み。
  B_ONLY_SAFE=0.01、CORE_AB_CONFIRM=0.02 の想定に戻っている。
  sender lot passthrough validation も PASS 済み。
```

---

## 参照した決定時doc / 現在doc

```text
docs/GOLD_C_ENV_RR2_72H_SIGNAL_DESIGN.md
docs/GOLD_H1H4_BEAR_AB_DRY_RUN_VALIDATION_NOTES.md
docs/GOLD_FIRST_SCOPE_AND_SIGNAL_INVENTORY.md
```

参照した現在コード:

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
scripts/research_gold_c_env_rr2_72h_notification_and_intent_preview.py
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
scripts/run_gold_h1h4_bear_ab_dry_run_loop.py
scripts/run_gold_multi_strategy_dry_run_cycle.py
scripts/send_mt5_order_from_payload.py
scripts/run_gold_sender_lot_passthrough_validation.py
```

---

## BUY_C_ENV_RR2_72H 仕様照合

決定時 strategy id:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

現在コードでも同じcondition id / strategy idを使用。

### 一致している条件

H4 environment:

```text
H4 ema20 > H4 ema50
H4 close > H4 ema50
```

H1 regular bullish divergence:

```text
pivot lows left=2/right=2
current_pivot_low < previous_pivot_low
current_pivot_macd > previous_pivot_macd
loose exhaustion:
  H1 close_at_confirm < H1 ema50_at_confirm
  OR H1 ema20_at_confirm < H1 ema50_at_confirm
```

M15 trigger:

```text
M15 close > high.shift(1).rolling(8).max()
M15 close > M15 ema20
M15 MACD > M15 MACD signal
M15 MACD histogram > previous histogram
```

Entry:

```text
BUY only
entry_time = M15 close_time
entry_price_reference = M15 close
entry_type = MARKET_ON_SIGNAL
```

SL/TP:

```text
SL = H1 regular bullish pivot low - M15 ATR14 * 0.05
TP = entry_price + (entry_price - SL) * 2.0
RR = 2.0
```

Exit:

```text
TP/SL first-touch
unresolved after 72h => time exit at last M5 close before 72h horizon
same M5 candle conflict => SL priority
```

### 統合時に落としてはいけない重要条件

```text
M5 coverage rule:
  entry before first available M5 candle must be NO_M5_PATH
  missing M5 history must not be skipped to judge old entries using later M5 data

latest-confirmed-policy:
  default last
  use second_last if live CSV includes forming candle

Separation policy:
  do not mutate existing Mochipoyo trigger-state / notification ledger / autotrade files until promoted
```

### BUY側のlot注意

BUY_C_ENVのorder intentは現在 `lot=None` / `lot_status=NOT_CALCULATED_RESEARCH_PREVIEW` であり、lotはまだ戦略仕様として固定されていない。

統合時は、別途 base_lot 0.01 等を明示的に決めてpayloadへ入れる必要がある。

---

## SELL_H1H4_BEAR_AB 仕様照合

決定時 strategy family:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

現在コードも同じfamilyを使用。

### rank仕様は一致

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

### A条件は一致

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

### B条件は一致

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

### base_lot default 相違と修正結果

修正前:

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py:
  --base-lot default = 0.10

scripts/run_gold_h1h4_bear_ab_dry_run_loop.py:
  --base-lot default = 0.10

scripts/run_gold_multi_strategy_dry_run_cycle.py:
  SELL runner呼び出し時に --base-lot 0.01 を明示していなかった
```

修正後:

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py:
  --base-lot default = 0.01

scripts/run_gold_h1h4_bear_ab_dry_run_loop.py:
  --base-lot default = 0.01

scripts/run_gold_multi_strategy_dry_run_cycle.py:
  SELL runner呼び出し時に --base-lot 0.01 を明示
```

現在の想定lot:

```text
base_lot 0.01 の場合:
  CORE_AB_CONFIRM -> 0.02
  B_ONLY_SAFE     -> 0.01
  A_ONLY_OBSERVE  -> 0.00 / 注文なし
```

### sender lot passthrough validation

追加済み:

```text
scripts/run_gold_sender_lot_passthrough_validation.py
```

実行結果:

```text
validation_ok=true
reason=GOLD_SENDER_LOT_PASSTHROUGH_VALIDATION_PASS
payload_lot=0.02
sender_lot_values=[0.02]
sender_lot_ok=true
registry_lot_values=[0.02]
registry_lot_ok=true
sender_dry_run_check_ok_rows=1
sender_error_rows=0
sender_order_send_called_count=0
sender_sent_rows=0
```

確認できたこと:

```text
payload lot=0.02 は sender 側で 0.02 のまま保持される。
registry preview でも 0.02 のまま保持される。
NO --send のため order_send は呼ばれていない。
```

---

## 複数ポジション/逆方向シグナル方針

ユーザー方針:

```text
別シグナルなら複数ポジションOK。
H1下落SELLの途中でも、別ロジックのBUYが上昇調整を取れるなら止めない。
BUY/SELL同時保有も、別ロジック・別時間軸なら許容。
```

統合で禁止すること:

```text
銘柄単位 block_any を新multi-strategy全体へ強制する。
GOLDポジションがあるだけで新シグナルを止める。
SELL保有中という理由だけでBUYを止める。
BUY保有中という理由だけでSELLを止める。
```

統合で止めるべきこと:

```text
同じ order_key の再送。
同じ signal_key の再送。
同じ strategy_id + confirmed_m15_time の重複。
同じ戦略スロットで同じ足に何度も出る重複。
```

---

## 統合前チェック状態

```text
1. SELL base_lot default 0.10 問題を修正する。
   -> DONE

2. BUY_C_ENV のlotを統合時に明示する。
   -> TODO

3. sender側でpayload lot/effective_lotを尊重する経路を確認する。
   -> DONE: lot passthrough validation PASS

4. 新GOLD multi-strategyを銘柄単位block_anyではなく、signal/order key単位重複防止で接続する。
   -> TODO

5. 既存もちぽよGOLD実運用BATは、上記修正後に統合する。
   -> TODO
```

---

## 現時点の結論

```text
シグナル条件そのものは、BUY/SELLとも決定時仕様と大筋一致。
SELLのロットdefault相違は修正済み。
A+B 0.02 lot は sender でも 0.02 のまま通ることを確認済み。
残る統合前論点は BUY_C_ENV の lot 明示と、signal/order key 単位の重複防止接続。
```
