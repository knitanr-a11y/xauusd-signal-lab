# NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS

## 目的

GOLD市場停止中のため、GOLD strategy sidecar とは分離して、BTC manual demo order_send smoke test の no-send / order_check まで PASS した状態を次チャットへ引き継ぐ。

これは GOLD multi-strategy signal ではない。

これは BTC strategy integration でもない。

これは **MT5 demo order_send 経路の手動 smoke test**。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS.md
```

GOLD sidecar の最新状態として併読推奨:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_COMPACT_CONSOLE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_WRAPPER.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN.md
```

---

## BTC manual smoke test の位置づけ

```text
目的: MT5 demo order path の接続確認
対象: BTCUSD#
口座: XMTrading demo login 75539039
実注文: まだしていない
send flag: まだ渡していない
order_send_called_count: 0
sent_rows: 0
production registry write: なし
```

GOLD strategy signal とは分離。

```text
gold_strategy_signal_used=false
btc_strategy_integration_used=false
```

---

## 追加済みファイル

```text
scripts/run_btc_manual_demo_order_send_smoke_test.py
```

役割:

```text
1. MT5 initialize
2. expected-login guard
3. demo account guard
4. BTC symbol resolve / select
5. symbol_info / tick 取得
6. BTC manual fixture payload 作成
7. send_mt5_order_from_payload.py を --send なしで実行
8. order_check OK を確認
9. order_send_called_count=0 / sent_rows=0 を確認
```

---

## 実行コマンド

```bat
python scripts\run_btc_manual_demo_order_send_smoke_test.py
```

出力先:

```text
data\r\btc_manual_demo_order_send_smoke_test
```

summary:

```text
data\r\btc_manual_demo_order_send_smoke_test\latest_btc_manual_demo_order_send_smoke_test_result.json
```

payload:

```text
data\r\btc_manual_demo_order_send_smoke_test\payload\btc_manual_order_payloads.csv
```

sender output:

```text
data\r\btc_manual_demo_order_send_smoke_test\sender_no_send
```

isolated ledger:

```text
data\r\btc_manual_demo_order_send_smoke_test\btc_manual_demo_order_ledger.csv
```

registry preview only:

```text
data\r\btc_manual_demo_order_send_smoke_test\registry_preview\registry_preview.csv
data\r\btc_manual_demo_order_send_smoke_test\registry_preview\registry_preview.json
```

---

## 実行結果

2回目の最終確認結果:

```text
cycle_ok=true
reason=BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS
symbol=BTCUSD#
direction=BUY
lot=0.01
entry_price_reference=80763.3
sl_price=80650.8
tp_price=80875.8
sender_returncode=0
sender_rows_out=1
sender_dry_run_check_ok_rows=1
sender_error_rows=0
sender_order_send_called_count=0
sender_sent_rows=0
```

sender側確認:

```text
send_requested=false
account_login=75539039
account_server=XMTrading-MT5 3
account_name=Demo Account
terminal_trade_allowed=true
account_trade_allowed=true
position_policy=block_any
max_symbol_positions=1
max_symbol_lot=0.01
order_send_called_count=0
dry_run_check_ok_rows=1
sent_rows=0
blocked_position_policy_rows=0
error_rows=0
registry_preview_enabled=true
registry_preview_rows=1
```

order_check row:

```text
order_status=DRY_RUN_ORDER_CHECK_OK
broker_symbol=BTCUSD#
direction=BUY
lot=0.01
existing_symbol_positions=0
existing_symbol_lot=0
current_execution_price=80763.3
sl_price=80650.8
tp_price=80875.8
order_check_ok=true
order_send_called=false
order_send_ok=false
validation_errors=
```

Safety:

```text
send_flag_passed=false
order_send_called_count=0
sent_rows=0
production_registry_mutated=false
gold_strategy_signal_used=false
btc_strategy_integration_used=false
existing_mochipoyo_bat_modified=false
existing_mochipoyo_ledgers_mutated=false
trigger_state_mutated=false
```

---

## 修正済み表示バグ

初回実行時、summary は保存されていたが、コンソール表示の `summary_json` が null になっていた。

修正済み:

```text
bef464e8a487568a6f9771393a9bc4fd6941792d
Fix BTC smoke test summary path display
```

修正後、表示も正常。

```text
summary_json=data\r\btc_manual_demo_order_send_smoke_test\latest_btc_manual_demo_order_send_smoke_test_result.json
```

---

## BTC no-send smoke test のコミット

```text
a785b895d7a309032a695bb5f5e08582ff7bdae9
Add BTC manual demo order send smoke test no-send runner

bef464e8a487568a6f9771393a9bc4fd6941792d
Fix BTC smoke test summary path display
```

---

## 現在のGOLD sidecar到達点

```text
Case Matrix: PASS
Monitor skip A/B: PASS
Same-M15 no-signal skip A/B: PASS
Guarded demo-send safety validation: PASS
Standard validation BAT: ALL PASS
sidecar dry-run単発: PASS
forever aligned dry-run: PASS
毎分02秒起動: OK
same-M15 no-signal skip: OK
no-send BAT: PASS
allow-only BAT: PASS
aligned compact console 1-cycle: PASS
aligned forever .bat launcher: PASS
aligned status viewer: PASS
aligned PowerShell launcher: PASS
Ctrl+C graceful stop: PASS
pre-cycle Ctrl+C summary preservation: PASS
status viewer fallback recovery: PASS
final status viewer summary_json recovery: PASS
signal-present fixture validation: PASS
payload_rows=1 guarded gate validation: PASS
order_send_called_count=0
sent_rows=0
production registry writeなし
```

---

## まだ作っていないもの / まだやらないこと

以下はまだ作っていない。

```text
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_armed.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_demo_send_and_send.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_send.bat
```

以下はまだ実施していない。

```text
BTC MT5 demo order_send
GOLD MT5 demo order_send
実CSV GOLD signal あり状態での --allow-demo-send --send 実行
send成功後の production registry write
close intent MT5 execution
BTC strategy integration
既存 Mochipoyo 本体BATへの統合
```

---

## 次に進む場合の推奨

次に実注文テストへ進むなら、BTCで **manual demo send-once** を別枠で作る。

ただし、以下を必須にする。

```text
別ファイル
別out-dir
別ledger
別magic
expected-login=75539039 必須
require-demo-account 必須
symbol=BTCUSD# 固定または明示
max-orders=1
position-policy=block_any
max-symbol-positions=1
max-symbol-lot=0.01
最小lot=0.01
SL/TP は現在価格から自動算出
production registry writeなし
ユーザー明示承認なしでは --send を渡さない
```

推奨ファイル名:

```text
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
```

この send-once runner も二重承認にする。

```text
--allow-demo-send と --send の両方が揃った時だけ sender に --send を渡す
```

さらに、初回は runner を作るだけで、実行はしない。

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md

現在は、GOLDのBUY/SELL multi-strategyを既存もちぽよ本体に直接混ぜず、独立したsidecar dry-run / guarded demo send flowとして構築中です。

GOLD市場が止まっているため、実注文経路の確認はGOLD strategy signalとは分離し、BTC manual demo order_send smoke test として進めています。

BTC no-send / order_check smoke test 到達点:
- scripts/run_btc_manual_demo_order_send_smoke_test.py 追加済み
- python scripts\run_btc_manual_demo_order_send_smoke_test.py 実行済み
- cycle_ok=true
- reason=BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS
- symbol=BTCUSD#
- direction=BUY
- lot=0.01
- sender_rows_out=1
- sender_dry_run_check_ok_rows=1
- sender_error_rows=0
- sender_order_send_called_count=0
- sender_sent_rows=0
- send_flag_passed=false
- production_registry_mutated=false
- gold_strategy_signal_used=false
- btc_strategy_integration_used=false

重要:
- まだ BTC MT5 demo order_send はしていない
- まだ BTC send-once runner/BAT は作っていない
- まだ GOLD MT5 demo order_send はしていない
- まだ production registry write は実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC strategy integrationはまだ触らない

次にやること:
1. BTC manual demo send-once runner を別ファイルで設計/作成する
2. --allow-demo-send と --send の二重承認必須
3. expected-login / require-demo-account / max-orders=1 / block_any / max-symbol-lot=0.01 を固定
4. 作成しても、ユーザー明示承認なしでは実行しない
```

---

## 現時点の結論

```text
BTC no-send / order_check smoke test は PASS。
MT5接続・BTCUSD#・demo guard・order_check までは正常。
次に進むなら、BTC manual demo send-once runner を二重承認付きで作る段階。
実注文はまだしていない。
```
