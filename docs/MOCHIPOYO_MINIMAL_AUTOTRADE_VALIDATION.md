# MOCHIPOYO MINIMAL AUTO-TRADE VALIDATION

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 GOLD minimal live flow から MT5 デモ口座への自動発注までの検証ログである。

対象は **デモ口座** のみ。
本口座での実運用はまだ未実施。

---

## 1. 現在の総合到達点

```text
GOLD minimal live loop: PASS
Discord実送信: PASS
order payload生成: PASS
MT5デモ口座接続: PASS
GOLD# symbol/tick取得: PASS
MT5 order_check: PASS
デモ口座単体 order_send: PASS
position policy: PASS
live loop内 auto-trade dry-run: PASS
live loop内 auto-trade send: PASS
既存ポジション時の追加発注ブロック: PASS
候補0件時の全段safe skip: PASS
短時間デモauto-trade bat作成: PASS
```

重要:

```text
本口座での自動売買は未実施。
現在の発注検証は XMTrading デモ口座のみ。
```

---

## 2. MT5接続確認

追加スクリプト:

```text
scripts/check_mt5_connection_and_symbol.py
```

まず `MetaTrader5` Python package が未導入で失敗した。

```text
ModuleNotFoundError("No module named 'MetaTrader5'")
```

対応:

```cmd
python -m pip install MetaTrader5
```

本口座で `GOLD` はNG、`GOLD#` はPASS。

本口座確認結果:

```text
account_login: 72397804
account_server: XMTrading-MT5 3
symbol: GOLD#
symbol_select_ok: True
symbol_info_ok: True
symbol_tick_ok: True
trade_allowed_terminal: False
trade_allowed_account: True
order_sent: False
```

その後、デモ口座へ切り替え。

デモ口座確認結果:

```text
account_login: 75539039
account_server: XMTrading-MT5 3
account_name: Demo Account
symbol: GOLD#
symbol_select_ok: True
symbol_info_ok: True
symbol_tick_ok: True
bid/ask取得: OK
digits: 2
point: 0.01
volume_min: 0.01
volume_step: 0.01
volume_max: 50.0
trade_stops_level: 0
trade_freeze_level: 0
spread_price_tick: 約0.29〜0.30
order_sent: False
```

判定:

```text
MT5デモ接続: PASS
GOLD#確認: PASS
```

---

## 3. order payload dry-run

追加スクリプト:

```text
scripts/build_mochipoyo_order_payloads.py
```

検証コマンド:

```cmd
python scripts\build_mochipoyo_order_payloads.py --input-csv data\results\mochipoyo\minimal_ledger_test\run1\notification_ledger_to_send.csv --output-csv data\results\mochipoyo\order_payload_dryrun_test\gold_order_payloads.csv --output-json data\results\mochipoyo\order_payload_dryrun_test\gold_order_payloads.json --symbol GOLD --broker-symbol GOLD --fixed-lot 0.01 --magic 26050601 --max-orders 5
```

結果:

```text
rows_in: 46
rows_out: 5
valid_order_payloads: 5
invalid_order_payloads: 0
```

主なpayload例:

```text
GOLD_H4_M5_SCALP SELL 0.01
GOLD_H4_M15_DAYTRADE BUY 0.01
```

判定:

```text
order payload dry-run: PASS
```

---

## 4. MT5 order_check 検証

追加スクリプト:

```text
scripts/check_mt5_order_payloads.py
```

目的:

```text
order_payloads.csv を読む
MT5のGOLD# symbol_info/tickを読む
lot が volume_min/step/max に合うか確認
SL/TP が BUY/SELL方向に正しいか確認
order_check だけ実行
order_send は絶対に呼ばない
```

local validation:

```cmd
python scripts\check_mt5_order_payloads.py --input-csv data\ml_loop_orderdry_test1\iter_0001\order\order_payloads.csv --out-dir data\mt5_order_check_goldsharp_local --symbol GOLD# --select-symbol
```

結果:

```text
local_validation_ok_rows: 1
local_validation_ng_rows: 0
run_order_check: False
order_send_called: False
```

order_check:

```cmd
python scripts\check_mt5_order_payloads.py --input-csv data\ml_loop_orderdry_test1\iter_0001\order\order_payloads.csv --out-dir data\mt5_order_check_goldsharp_ordercheck_v2 --symbol GOLD# --select-symbol --run-order-check
```

結果:

```text
local_validation_ok_rows: 1
local_validation_ng_rows: 0
order_check_ok_rows: 1
order_check_ng_rows: 0
order_check_retcode: 0
order_check_comment: Done
order_send_called: False
```

注意:

```text
XM/MT5 の order_check は retcode=0 / comment=Done が成功扱い。
当初 10009 のみOK扱いにしていたため誤判定したが修正済み。
```

判定:

```text
MT5 order_check: PASS
実発注なし: PASS
```

---

## 5. デモ口座単体 order_send 検証

追加スクリプト:

```text
scripts/send_mt5_order_from_payload.py
```

安全仕様:

```text
デフォルトはdry-run
--send を付けない限り order_send しない
max-orders はデフォルト1
order_check PASS後だけ order_send
expected-login でデモ口座番号を固定可能
require-demo-account でデモ口座ガード可能
order ledgerで同じorder_keyの二重発注を防止
position policyで既存ポジションを制御
```

単体dry-run:

```cmd
python scripts\send_mt5_order_from_payload.py --input-csv data\ml_loop_orderdry_test1\iter_0001\order\order_payloads.csv --order-ledger-csv data\mt5_demo_order_test\goldsharp_order_ledger.csv --out-dir data\mt5_demo_order_test\dryrun1 --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039
```

結果:

```text
send_requested: False
account_login: 75539039
account_name: Demo Account
order_send_called_count: 0
dry_run_check_ok_rows: 1
sent_rows: 0
error_rows: 0
order_status: DRY_RUN_ORDER_CHECK_OK
```

単体send:

```cmd
python scripts\send_mt5_order_from_payload.py --input-csv data\ml_loop_orderdry_test1\iter_0001\order\order_payloads.csv --order-ledger-csv data\mt5_demo_order_test\goldsharp_order_ledger.csv --out-dir data\mt5_demo_order_test\send1 --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --send
```

結果:

```text
send_requested: True
account_login: 75539039
account_name: Demo Account
broker_symbol: GOLD#
direction: BUY
lot: 0.01
order_check_ok: True
order_send_called: True
order_send_ok: True
order_send_retcode: 10009
order_send_comment: Request executed
order_status: SENT
order_ticket: 945716928
deal_ticket: 932062656
error_rows: 0
```

MT5取引タブ確認:

```text
GOLD# BUY 0.01 が実際に表示された。
```

判定:

```text
デモ口座単体 order_send: PASS
```

---

## 6. position policy 検証

`send_mt5_order_from_payload.py` に追加済み:

```text
--position-policy block_any
--position-policy allow_same_direction
--position-policy allow_any_until_max
--max-symbol-positions
--max-symbol-lot
```

### 6.1 block_any / 既存ポジションブロック

既存 `GOLD# BUY 0.01` がある状態で再実行。

結果:

```text
existing_symbol_positions: 1
order_status: BLOCKED_EXISTING_SYMBOL_POSITION / BLOCKED_POSITION_POLICY
order_send_called_count: 0
sent_rows: 0
```

判定:

```text
既存ポジションガード: PASS
```

### 6.2 allow_same_direction dry-run

既存 `GOLD# BUY 0.01` がある状態で、同方向BUY 0.01追加をdry-run。

```cmd
python scripts\send_mt5_order_from_payload.py --input-csv data\ml_loop_orderdry_test1\iter_0001\order\order_payloads.csv --order-ledger-csv data\mt5_demo_order_test\goldsharp_order_ledger_position_policy_test.csv --out-dir data\mt5_demo_order_test\position_policy_same_direction_dryrun1 --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --position-policy allow_same_direction --max-symbol-positions 2 --max-symbol-lot 0.02
```

結果:

```text
position_policy: allow_same_direction
existing_symbol_positions: 1
existing_symbol_lot: 0.01
existing_symbol_directions: BUY
dry_run_check_ok_rows: 1
blocked_position_policy_rows: 0
error_rows: 0
order_send_called_count: 0
```

判定:

```text
allow_same_direction dry-run: PASS
```

### 6.3 allow_same_direction send

```cmd
python scripts\send_mt5_order_from_payload.py --input-csv data\ml_loop_orderdry_test1\iter_0001\order\order_payloads.csv --order-ledger-csv data\mt5_demo_order_test\goldsharp_order_ledger_position_policy_test.csv --out-dir data\mt5_demo_order_test\position_policy_same_direction_send1 --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --position-policy allow_same_direction --max-symbol-positions 2 --max-symbol-lot 0.02 --send
```

結果:

```text
position_policy: allow_same_direction
existing_symbol_positions: 1
existing_symbol_lot: 0.01
existing_symbol_directions: BUY
order_send_called_count: 1
sent_rows: 1
error_rows: 0
order_status: SENT
order_send_retcode: 10009
order_send_comment: Request executed
order_ticket: 945722523
deal_ticket: 932067778
```

判定:

```text
allow_same_direction 追加発注: PASS
```

### 6.4 max positions / max lot block

既存 `GOLD# BUY 0.02` の状態で、さらにBUY 0.01を試行。

結果:

```text
existing_symbol_positions: 2
existing_symbol_lot: 0.02
existing_symbol_directions: BUY,BUY
order_status: BLOCKED_POSITION_POLICY
order_send_called_count: 0
sent_rows: 0
blocked_position_policy_rows: 1
```

ブロック理由:

```text
position count limit exceeded: after_count=3; max_symbol_positions=2
position lot limit exceeded: after_lot=0.03; max_symbol_lot=0.02
```

判定:

```text
max positions / max lot block: PASS
```

---

## 7. live loop auto-trade dry-run 検証

`run_mochipoyo_gold_minimal_live_loop_dry.py` に追加済み:

```text
--enable-auto-trade-dry-run
--auto-trade-broker-symbol
--auto-trade-order-ledger-csv
--auto-trade-expected-login
--auto-trade-select-symbol
--auto-trade-require-demo-account
--auto-trade-position-policy
--auto-trade-max-symbol-positions
--auto-trade-max-symbol-lot
--auto-trade-max-orders
--auto-trade-deviation
```

仕様:

```text
send_mt5_order_from_payload.py を --send なしで呼ぶ。
MT5接続とorder_checkまでは行う。
order_send は呼ばない。
```

### 7.1 既存ポジションあり / safe block

既存ポジションがある状態で `block_any`。

結果:

```text
discord_status: SENT
order_payload_status: OK
order_payload_rows: 1
valid_order_payloads: 1
auto_trade_status: OK_BLOCKED_POSITION_POLICY
auto_trade_rows: 1
auto_trade_blocked_position_policy_rows: 1
auto_trade_order_send_called_count: 0
auto_trade_sent_rows: 0
success: True
```

判定:

```text
live loop auto-trade dry-run position-policy safe block: PASS
```

### 7.2 flat状態 / order_check OK

2件のデモポジションを手動決済後、flat状態でdry-run。

結果:

```text
discord_status: SENT
order_payload_status: OK
order_payload_rows: 1
valid_order_payloads: 1
auto_trade_status: OK
auto_trade_send_enabled: False
auto_trade_rows: 1
auto_trade_dry_run_check_ok_rows: 1
auto_trade_blocked_position_policy_rows: 0
auto_trade_order_send_called_count: 0
auto_trade_sent_rows: 0
success: True
```

判定:

```text
live loop auto-trade dry-run flat/order_check: PASS
```

---

## 8. live loop auto-trade send 検証

`run_mochipoyo_gold_minimal_live_loop_dry.py` に追加済み:

```text
--enable-auto-trade-send
```

安全仕様:

```text
--enable-auto-trade-send を明示した時だけ send_mt5_order_from_payload.py に --send を渡す
--enable-auto-trade-dry-run と --enable-auto-trade-send の同時指定は禁止
--enable-auto-trade-send では --auto-trade-expected-login が必須
--enable-auto-trade-send では --auto-trade-require-demo-account が必須
send_mt5_order_from_payload.py 側の order_key重複 / account / demo / position_policy / order_check ガードを通った時だけ発注
```

### 8.1 flat状態 / loopから1件send

コマンド概要:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_loop_dry.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\ml_loop_autotrade_send_test1 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_live_once_discord_send_test\artificial_commit_test\gold_pair_trigger_state_test.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_discord_send_test\artificial_commit_test\gold_notification_ledger_fresh_test.csv --iterations 1 --sleep-seconds 1 --commit-trigger-state --commit-ledger --discord-send --discord-max-rows 5 --discord-style compact --enable-order-payload-dry-run --order-broker-symbol GOLD# --order-fixed-lot 0.01 --order-magic 26050601 --order-max-rows 5 --enable-auto-trade-send --auto-trade-broker-symbol GOLD# --auto-trade-order-ledger-csv data\mt5_demo_order_test\goldsharp_auto_trade_loop_order_ledger.csv --auto-trade-expected-login 75539039 --auto-trade-select-symbol --auto-trade-require-demo-account --auto-trade-position-policy block_any --auto-trade-max-symbol-positions 1 --auto-trade-max-symbol-lot 0.01 --auto-trade-max-orders 1 --stop-on-error
```

結果:

```text
discord_status: SENT
order_payload_status: OK
order_payload_rows: 1
valid_order_payloads: 1
auto_trade_status: SENT
auto_trade_send_enabled: True
auto_trade_rows: 1
auto_trade_order_send_called_count: 1
auto_trade_sent_rows: 1
success: True
```

MT5取引タブ確認:

```text
GOLD# BUY 0.01 が実際に表示された。
```

判定:

```text
live loop auto-trade send: PASS
```

### 8.2 既存ポジションあり / loopから追加発注ブロック

上記発注後、既存 `GOLD# BUY 0.01` がある状態で同様にsend。

結果:

```text
discord_status: SENT
order_payload_status: OK
order_payload_rows: 1
valid_order_payloads: 1
auto_trade_status: OK_BLOCKED_POSITION_POLICY
auto_trade_send_enabled: True
auto_trade_rows: 1
auto_trade_blocked_position_policy_rows: 1
auto_trade_order_send_called_count: 0
auto_trade_sent_rows: 0
success: True
```

判定:

```text
live loop auto-trade send duplicate/position block: PASS
```

### 8.3 候補0件 / 全段safe skip

通常のtrigger state / production ledgerで短時間loopを実行。
候補が0件の場合、以前は `notification_ledger_to_send.csv` 読み込みで `ERROR_READ_TO_SEND` になっていた。
修正後は候補0件を正常スキップ扱いにした。

修正コミット:

```text
623faf954b4922f6a0dbcb21228c3a2224f635f2
  Treat no notification rows as safe order-payload skip
```

確認結果:

```text
iteration 1:
  pairs_to_scan = 3
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 45
  ledger_new_candidates = 0
  discord_status = SKIPPED_NO_ROWS
  order_payload_status = SKIPPED_NO_ROWS
  auto_trade_status = SKIPPED_NO_ORDER_PAYLOAD_ROWS
  auto_trade_order_send_called_count = 0
  auto_trade_sent_rows = 0
  success = True

iteration 2:
  pairs_to_scan = 0
  discord_status = SKIPPED_NO_ROWS
  order_payload_status = SKIPPED_NO_ROWS
  auto_trade_status = SKIPPED_NO_ORDER_PAYLOAD_ROWS
  success = True

iteration 3:
  pairs_to_scan = 0
  discord_status = SKIPPED_NO_ROWS
  order_payload_status = SKIPPED_NO_ROWS
  auto_trade_status = SKIPPED_NO_ORDER_PAYLOAD_ROWS
  success = True
```

判定:

```text
候補0件時の全段safe skip: PASS
order_send未呼び出し: PASS
```

---

## 9. 短時間デモauto-trade bat

追加済み:

```text
scripts/run_mochipoyo_gold_demo_autotrade_short.bat
```

目的:

```text
長いコマンドを毎回手入力しない。
デモ口座限定で、短時間だけDiscord送信 + MT5 auto-trade send loopを起動する。
```

batの固定安全設定:

```text
account expected-login: 75539039
require demo account: ON
broker_symbol: GOLD#
lot: 0.01
position_policy: block_any
max_symbol_positions: 1
max_symbol_lot: 0.01
auto_trade_max_orders: 1
iterations: 3
sleep_seconds: 10
out-dir: data\ml_loop_demo_prod_short
```

使い方:

```cmd
scripts\run_mochipoyo_gold_demo_autotrade_short.bat
```

実行前チェック:

```text
MT5がXMTradingデモ口座 75539039 でログイン中
Algo Trading ON
.env にDiscord Webhookあり
本口座ではない
既存GOLD#ポジションの有無を把握している
```

既存ポジションがある場合:

```text
position_policy block_any により追加発注はブロックされる。
```

候補0件の場合:

```text
Discord / order payload / auto-trade は全段safe skipされる。
```

---

## 10. 現在の安全な運用方針

まだ本口座では使わない。
次の段階は、デモ口座で短時間の実loopを必要な時だけ行うこと。

推奨方針:

```text
broker_symbol: GOLD#
account: XMTrading demo 75539039
lot: 0.01
position_policy: block_any
max_symbol_positions: 1
max_symbol_lot: 0.01
auto_trade_max_orders: 1
```

デモ口座での短時間運用コマンドは、必ず短い `out-dir` を使う。

```text
data/ml_loop_demo_prodX
```

避ける:

```text
data/results/mochipoyo/... の深いout-dir
```

---

## 11. まだやっていないこと

```text
本口座での自動売買
長時間のデモ auto-trade send loop
損益/ポジション管理
自動決済
建値移動
トレーリング
約定後のDiscord追跡通知
ポジション一覧監視
日次損失制限
連続発注間隔制限
時間帯停止
```

現状はエントリー自動発注まで。
決済はSL/TPをMT5注文に付けているのみ。

---

## 12. 次にやるなら

長めloopはユーザー希望により行わない。
推奨順:

```text
1. 必要な時だけ短時間batでデモ稼働
2. loop中の no-row / blocked / sent のsummary確認
3. order ledgerとMT5履歴の照合
4. ポジション監視スクリプト追加
5. 約定後Discord追跡通知
6. 本口座検討は十分なデモ確認後
```

最重要注意:

```text
本口座ではまだ実行しない。
--enable-auto-trade-send はデモ口座 expected-login と require-demo-account を必須にして使う。
```
