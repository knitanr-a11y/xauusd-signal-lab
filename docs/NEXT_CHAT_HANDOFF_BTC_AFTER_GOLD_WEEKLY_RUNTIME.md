# NEXT_CHAT_HANDOFF_BTC_AFTER_GOLD_WEEKLY_RUNTIME

## 目的

次チャットで BTC 側を、GOLD と同じ基本機能・安全設計で構築するための引き継ぎ。

GOLD 側では、既存もちぽよGOLDと新GOLD multi-strategyを別枠で動かす構成まで到達した。
BTC は GOLD 完了後に別枠BATとして作る方針。

---

## 現在のGOLD到達点

GOLDは2本運用。

### 1. 既存もちぽよGOLD

起動BAT:

```bat
scripts\run_mochipoyo_gold_demo_autotrade_forever_aligned_weekly_logs.bat
```

役割:

```text
既存もちぽよGOLDシグナルを監視
Discord通知
GOLD# デモ発注
既存trigger-state / notification-ledger / order-ledgerを使用
ログは年/月/週フォルダへ保存
エラー停止時は notify_mochipoyo_loop_stopped.py でDiscord通知
```

ログ:

```text
data\runtime_logs\gold\YYYY\MM\week_XX\mochipoyo_gold\loop\
```

主なCSV:

```text
data\runtime_logs\gold\YYYY\MM\week_XX\mochipoyo_gold\loop\gold_minimal_live_loop_live_summary.csv
```

固定state/ledger:

```text
data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv
data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv
data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv
```

### 2. 新GOLD multi-strategy

起動BAT:

```bat
scripts\run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
```

役割:

```text
新GOLD multi-strategyを監視
シグナルがなければ NO_PAYLOAD_ROWS / SAFE_NO_PAYLOAD_PASS で待機
シグナルが出たら guarded demo send へ進む
--allow-demo-send と --send が両方ある時のみ senderへ --send を渡す
ログは年/月/週フォルダへ保存
order_key重複防止ledgerは固定stateへ保存
エラー停止時は notify_mochipoyo_loop_stopped.py でDiscord通知
```

ログ:

```text
data\runtime_logs\gold\YYYY\MM\week_XX\multi_strategy_gold\loop\
```

主なCSV/JSON:

```text
data\runtime_logs\gold\YYYY\MM\week_XX\multi_strategy_gold\loop\aligned_loop_log.csv
data\runtime_logs\gold\YYYY\MM\week_XX\multi_strategy_gold\loop\latest_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_result.json
```

固定state:

```text
data\runtime_state\gold\multi_strategy\guarded_demo_order_ledger.csv
```

---

## GOLD新multi-strategyのシグナル仕様

### BUY_C_ENV_RR2_72H

strategy id:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

概要:

```text
H4 C_ENV:
  ema20 > ema50
  close > ema50

H1 regular bullish divergence:
  pivot lows left=2/right=2
  current_pivot_low < previous_pivot_low
  current_pivot_macd > previous_pivot_macd
  loose exhaustion:
    H1 close < H1 ema50 OR H1 ema20 < H1 ema50

M15 trigger:
  close > previous rolling high 8
  close > ema20
  MACD > signal
  MACD histogram increasing

Entry:
  BUY only
  M15 close_time
  M15 close

SL:
  H1 pivot low - M15 ATR14 * 0.05

TP:
  RR2

Exit:
  TP/SL first-touch
  unresolved after 72h = time exit
  same M5 candle conflict = SL priority
```

lot:

```text
base_lot=0.01
lot_multiplier=1.0
lot=0.01
```

### SELL_H1H4_BEAR_AB

strategy family:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

rank:

```text
CORE_AB_CONFIRM = A and B
  trade_enabled=true
  lot_multiplier=2.0
  lot=0.02

B_ONLY_SAFE = B and not A
  trade_enabled=true
  lot_multiplier=1.0
  lot=0.01

A_ONLY_OBSERVE = A and not B
  trade_enabled=false
  lot=0.00 / 注文なし
```

A条件:

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

B条件:

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

---

## GOLDで実施済みの重要修正

### SELL lot default修正

以下を base_lot=0.01 に修正済み。

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
scripts/run_gold_h1h4_bear_ab_dry_run_loop.py
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

現在:

```text
B_ONLY_SAFE=0.01
CORE_AB_CONFIRM=0.02
```

### BUY lot明示

以下で BUY_C_ENV order intent が lot=None にならないよう修正済み。

```text
scripts/research_gold_c_env_rr2_72h_notification_and_intent_preview.py
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
```

現在:

```text
base_lot=0.01
lot=0.01
volume=0.01
lot_status=CALCULATED_BASE_LOT
```

### sender lot passthrough validation

追加済み:

```text
scripts/run_gold_sender_lot_passthrough_validation.py
```

確認結果:

```text
payload_lot=0.02
sender_lot_values=[0.02]
registry_lot_values=[0.02]
sender_order_send_called_count=0
sent_rows=0
validation_ok=true
```

### order_key duplicate validation

追加済み:

```text
scripts/run_gold_sender_order_key_duplicate_validation.py
```

確認結果:

```text
position_policy=allow_any_until_max
position_policy_block_any_used=false
order_status_values=["BLOCKED_PRECHECK"]
validation_errors="duplicate order_key already exists in order ledger"
sender_order_send_called_count=0
sent_rows=0
validation_ok=true
```

---

## GOLD運用方針

GOLDは以下の2本を別ウィンドウで起動。

```bat
scripts\run_mochipoyo_gold_demo_autotrade_forever_aligned_weekly_logs.bat
scripts\run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
```

1つのBATへ統合しない理由:

```text
片方の停止がもう片方を巻き込むのを避ける
ログを分ける
既存もちぽよGOLDを壊さない
新multi-strategy側を独立sidecarとして運用する
```

新GOLD multi-strategy側の position policy:

```text
allow_any_until_max
```

理由:

```text
別シグナルなら複数ポジションOK
SELL中でも別ロジックBUYは止めない
BUY中でも別ロジックSELLは止めない
同じorder_keyだけ止める
```

禁止:

```text
新multi-strategy全体へ block_any を強制しない
GOLDポジションがあるだけで新シグナルを止めない
```

---

## BTCで流用すべきGOLD実装

BTCはGOLDとは別枠BAT・別ログ・別stateで作る。

流用候補:

### 1. sender

```text
scripts/send_mt5_order_from_payload.py
```

BTCでも流用。

重要引数:

```text
--symbol BTCUSD#
--expected-login 75539039
--require-demo-account
--select-symbol
--position-policy allow_any_until_max またはBTC仕様に合わせる
--max-orders 1
--deviation BTC向けに広め
--order-ledger-csv data/runtime_state/btc/.../guarded_demo_order_ledger.csv
```

### 2. 停止通知

```text
scripts/notify_mochipoyo_loop_stopped.py
```

BTCでも流用。

### 3. 週次ログ構成

GOLDの以下をBTC版へコピーして作る。

```text
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.py
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
```

BTC版の想定名:

```text
scripts/run_btc_guarded_demo_send_forever_aligned_weekly_state.py
scripts/run_btc_guarded_demo_send_forever_aligned_weekly_state.bat
```

ログ:

```text
data/runtime_logs/btc/YYYY/MM/week_XX/btc_strategy/loop/
```

固定state:

```text
data/runtime_state/btc/btc_strategy/guarded_demo_order_ledger.csv
```

### 4. no-payload safe wait

GOLDと同じく、BTCでもシグナルなしは正常待機扱い。

```text
payload_rows_out=0
send_flag_passed_to_sender=false
order_send_called_count=0
sent_rows=0
cycle_ok=true
cycle_ok_classification=SAFE_NO_PAYLOAD_PASS or NATURAL_PASS
```

### 5. guarded send

BTCでも、senderへ `--send` を渡す条件は必ず二重ロック。

```text
--allow-demo-send AND --send
```

payload_rows_out=0 の間は senderへ --send を渡さない。

---

## BTCで最初に確認すべきこと

次チャットでは、まずBTC既存資産を棚卸しする。

確認対象候補:

```text
BTC用CSV名 / MT5 symbol:
  BTCUSD# が実送信で成功済み

既存もちぽよBTCシグナルがあるか
既存BTC notification / scan / payload script があるか
BTCをGOLD既存もちぽよに含めるのではなく、別枠BATにする
BTC用ログ/state配置をGOLDと同型にする
```

BTCでは、過去に `run_btc_manual_demo_order_send_smoke_test.py` と `run_btc_manual_demo_order_send_smoke_test_send_once.py` を作って検証した。

確認済み:

```text
BTCUSD#
expected_login=75539039
require_demo_account=True
order_check OK
実送信 smoke test 成功
success marker による repeat send block も確認済み
```

次チャットで読むべき既存BTC関連スクリプト候補:

```text
scripts/run_btc_manual_demo_order_send_smoke_test.py
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
scripts/send_mt5_order_from_payload.py
```

BTC用に新規作成する可能性が高いもの:

```text
scripts/run_btc_guarded_demo_send_once.py
scripts/run_btc_guarded_demo_send_forever_aligned_weekly_state.py
scripts/run_btc_guarded_demo_send_forever_aligned_weekly_state.bat
```

---

## BTC作成時の注意

BTCはGOLDより価格桁・スプレッドが大きい。

注意点:

```text
価格桁がGOLDと違う
SL/TP距離をGOLD固定値から流用しない
deviationはBTC向けに広めにする
lotは0.01から開始
BTCは市場が開いているためorder_check / demo send検証は比較的やりやすい
```

ただし、BTCでも実シグナル未発生時の実送信fixtureは慎重に扱う。

GOLDで使ったmanual smoke testの思想を流用する:

```text
戦略シグナルではないmanual smoke testと、本番戦略flowを分ける
send once markerで繰り返し送信を防ぐ
本番flowはorder_key ledgerで重複防止
```

---

## BTC次チャットの推奨進行

1. BTC関連ファイルを読む
2. BTC用の現在存在するシグナル/スクリプトを棚卸し
3. BTCを既存もちぽよとは別枠として設計
4. GOLD weekly_state runnerをBTCへ移植
5. BTC用 payload builder / guarded once / forever aligned weekly state BAT を作る
6. no-send 1 cycle確認
7. order_check確認
8. guarded send-once確認
9. forever aligned weekly state BATで運用確認
10. BTCも停止時Discord通知を付ける

---

## 新チャットで最初に読むべきドキュメント

```text
docs/NEXT_CHAT_HANDOFF_BTC_AFTER_GOLD_WEEKLY_RUNTIME.md
docs/GOLD_SIGNAL_SPEC_AUDIT_BEFORE_INTEGRATION.md
docs/GOLD_FIRST_SCOPE_AND_SIGNAL_INVENTORY.md
```

BTC manual smoke testの履歴確認用に、必要なら以下も読む。

```text
scripts/run_btc_manual_demo_order_send_smoke_test.py
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
scripts/send_mt5_order_from_payload.py
```

---

## 新チャット貼り付け用指示文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

必須:
docs/NEXT_CHAT_HANDOFF_BTC_AFTER_GOLD_WEEKLY_RUNTIME.md
docs/GOLD_SIGNAL_SPEC_AUDIT_BEFORE_INTEGRATION.md
docs/GOLD_FIRST_SCOPE_AND_SIGNAL_INVENTORY.md

BTC関連で最初に確認:
scripts/run_btc_manual_demo_order_send_smoke_test.py
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
scripts/send_mt5_order_from_payload.py

現在の状況:
- GOLDは2本運用で一旦完成。
- 既存もちぽよGOLD:
  scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned_weekly_logs.bat
- 新GOLD multi-strategy:
  scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
- GOLDは年/月/週ログと固定stateを整理済み。
- 新GOLD multi-strategyの固定state:
  data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv

次はBTCをGOLDとは別枠BAT・別ログ・別stateで完成させたいです。
基本機能はGOLDと同じ予定です。

BTCの前提:
- broker symbol は BTCUSD#
- XMTrading demo login は 75539039
- BTC manual demo order_send smoke test は過去に成功済み
- BTCはGOLDとは別枠で作る
- GOLDで作った weekly_state runner / guarded send / order_key重複防止 / 停止時Discord通知 / 年月週ログ構成は流用してください
- BTCでもまず no-send 1 cycle、order_check、guarded send-once、forever aligned weekly state BAT の順で確認したいです
- 実運用はデモ口座なので、最終的には --allow-demo-send --send 付きBATで運用する想定です

まずはBTC既存資産の棚卸しから始めてください。
```
