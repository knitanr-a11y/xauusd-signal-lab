# NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS

## 目的

GOLD市場停止中に、GOLD strategy sidecar とは分離した **BTC manual demo order_send smoke test** として、BTCUSD# の demo send-once が PASS し、その後の再実行ブロックも PASS した状態を次チャットへ引き継ぐ。

これは GOLD multi-strategy signal ではない。

これは BTC strategy integration でもない。

これは **MT5 demo order_send 経路の手動 smoke test 成功記録**。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
```

併読推奨:

```text
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
```

---

## BTC manual send-once の位置づけ

```text
目的: MT5 demo order_send 経路の実送信確認
対象: BTCUSD#
口座: XMTrading demo login 75539039
実注文: 成功済み
send flag: --allow-demo-send --send の二重承認で sender に --send を渡した
production registry write: なし
GOLD strategy signal: 不使用
BTC strategy integration: 不使用
```

---

## 関連ファイル

no-send / order_check runner:

```text
scripts/run_btc_manual_demo_order_send_smoke_test.py
```

send-once guarded runner:

```text
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
```

send-once runner は以下を実装済み。

```text
--allow-demo-send と --send の二重承認
success marker による repeat-send block
repeat block 時は sender を呼ばない short-circuit
```

---

## 事前 no-send / order_check PASS

実行:

```bat
python scripts\run_btc_manual_demo_order_send_smoke_test.py
```

結果:

```text
cycle_ok=true
reason=BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS
symbol=BTCUSD#
direction=BUY
lot=0.01
sender_rows_out=1
sender_dry_run_check_ok_rows=1
sender_error_rows=0
sender_order_send_called_count=0
sender_sent_rows=0
send_requested=false
production_registry_mutated=false
```

---

## send-once 実行前 no-flag 抑止確認

実行:

```bat
python scripts\run_btc_manual_demo_order_send_smoke_test_send_once.py
```

結果:

```text
cycle_ok=true
mode=SUPPRESSED_NO_SEND_ORDER_CHECK_ONLY
reason=BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SUPPRESSED_NO_SEND_PASS
allow_demo_send=false
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
sender_rows_out=1
sender_dry_run_check_ok_rows=1
sender_order_send_called_count=0
sender_sent_rows=0
```

---

## send-once 実注文 PASS 1

実行:

```bat
python scripts\run_btc_manual_demo_order_send_smoke_test_send_once.py --allow-demo-send --send
```

結果:

```text
cycle_ok=true
mode=GUARDED_SEND_ONCE
reason=BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS
allow_demo_send=true
send_requested=true
send_flag_passed_to_sender=true
send_suppressed_reason=
symbol=BTCUSD#
direction=BUY
lot=0.01
entry_price_reference=80753.6
sl_price=80641.1
tp_price=80866.1
sender_returncode=0
sender_rows_out=1
sender_dry_run_check_ok_rows=0
sender_error_rows=0
sender_order_send_called_count=1
sender_sent_rows=1
```

sender row:

```text
order_status=SENT
broker_symbol=BTCUSD#
direction=BUY
lot=0.01
existing_symbol_positions=0
existing_symbol_lot=0
current_execution_price=80753.6
sl_price=80641.1
tp_price=80866.1
order_check_ok=true
order_send_called=true
order_send_ok=true
order_send_retcode=10009
order_send_comment=Request executed
order_ticket=946736969
deal_ticket=933029758
validation_errors=
```

---

## send-once 実注文 PASS 2 / marker 作成

success marker 実装後、marker がまだ無い状態で `--allow-demo-send --send` を実行したため、もう1件BTC demo注文が入った。

実行:

```bat
python scripts\run_btc_manual_demo_order_send_smoke_test_send_once.py --allow-demo-send --send
```

結果:

```text
success_marker_exists_before_run=false
send_flag_passed_to_sender=true
order_send_called_count=1
sent_rows=1
success_marker_written=true
```

注文:

```text
order_status=SENT
broker_symbol=BTCUSD#
direction=BUY
lot=0.01
current_execution_price=80771.8
sl_price=80659.3
tp_price=80884.3
order_check_ok=true
order_send_called=true
order_send_ok=true
order_send_retcode=10009
order_send_comment=Request executed
order_ticket=946737003
deal_ticket=933029780
```

marker:

```text
data\r\btc_manual_demo_order_send_smoke_test_send_once\btc_manual_send_once_success_marker.json
```

---

## repeat-send block PASS 1

marker 作成後、同じ `--allow-demo-send --send` を再実行した。

結果:

```text
success_marker_exists_before_run=true
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_ONCE_SUCCESS_MARKER_EXISTS_REPEAT_BLOCKED
order_send_called_count=0
sent_rows=0
repeat_send_blocked=true
```

ただし、この時点の実装では、repeat block 後も sender no-send check を呼んでいた。

そのため、既存BTCポジションにより以下が出た。

```text
order_status=BLOCKED_POSITION_POLICY
existing_symbol_positions=1
existing_symbol_lot=0.01
validation_errors=position policy block_any blocked order: existing_positions=1; existing_lot=0.01
cycle_ok=false
sender_error_rows=1
```

安全上は問題なし。追加注文は出ていない。

---

## repeat-send block PASS 2 / sender short-circuit

上記の運用表示を改善するため、repeat block 時は sender を呼ばずに正常ブロック扱いに修正済み。

修正コミット:

```text
d13b60b9364bd5d42438a65c0654a7bc8b471ac9
Short-circuit BTC send-once repeat block before sender
```

再確認:

```bat
python scripts\run_btc_manual_demo_order_send_smoke_test_send_once.py --allow-demo-send --send
```

結果:

```text
success_marker_exists_before_run=true
sender_invoked=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_ONCE_SUCCESS_MARKER_EXISTS_REPEAT_BLOCKED
cycle_ok=true
mode=REPEAT_SEND_BLOCKED_NO_SENDER
reason=BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_REPEAT_BLOCKED_PASS
sender_returncode=0
sender_rows_out=1
sender_dry_run_check_ok_rows=0
sender_error_rows=0
sender_order_send_called_count=0
sender_sent_rows=0
repeat_send_blocked=true
success_marker_written=false
```

Safety:

```text
sender_invoked=false
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

## 重要な注意

この注文は以下ではない。

```text
GOLD multi-strategy signal の実注文ではない
BTC strategy signal の実注文ではない
production registry write を伴う自動売買ではない
既存 Mochipoyo 本体統合ではない
```

これは手動 fixture による BTC demo order_send smoke test。

また、BTCUSD# BUY 0.01 は少なくとも2件入っている可能性があるため、MT5画面でポジションを確認し、必要なら手動決済する。

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

## BTC manual smoke test 到達点

```text
BTC no-send / order_check smoke test: PASS
BTC send-once guarded runner: PASS
BTC demo order_send: PASS
BTCUSD# BUY 0.01 sent at least once; likely two manual smoke-test BUY positions exist
order_send_retcode=10009
order_send_comment=Request executed
repeat-send marker: written
repeat-send block: PASS
repeat-send short-circuit before sender: PASS
production registry writeなし
```

---

## まだ作っていないもの / まだやらないこと

以下はまだ作っていない/未対応。

```text
BTC manual close smoke test
GOLD MT5 demo order_send
GOLD armed BAT
send成功後の production registry write
close intent MT5 execution
BTC strategy integration
既存 Mochipoyo 本体BATへの統合
```

---

## 次にやること

```text
1. BTCポジションはMT5画面で確認し、必要なら手動決済
2. BTC manual close smoke test を作るか検討
3. GOLD sidecar は引き続き dry-run / signal-present 待ち
4. GOLD実送信はまだしない
5. production registry write はまだ実装しない
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md

BTC manual demo order_send smoke test として、BTCUSD# BUY 0.01 の demo send-once が成功済みです。
これは GOLD strategy signal でも BTC strategy integration でもなく、MT5 demo order_send 経路の手動 smoke test です。

send-once 実行:
python scripts\run_btc_manual_demo_order_send_smoke_test_send_once.py --allow-demo-send --send

結果:
- BTC no-send/order_check PASS
- BTC send-once PASS
- order_status=SENT
- order_send_ok=true
- order_send_retcode=10009
- order_send_comment=Request executed
- order_ticket=946736969 / deal_ticket=933029758
- marker実装後にもう1件 send-once 成功: order_ticket=946737003 / deal_ticket=933029780
- success_marker_written=true
- repeat-send block PASS
- repeat block時は sender_invoked=false
- send_flag_passed_to_sender=false
- order_send_called_count=0
- sent_rows=0
- production_registry_mutated=false
- gold_strategy_signal_used=false
- btc_strategy_integration_used=false

重要:
- BTCUSD# BUY 0.01 が少なくとも2件入っている可能性があるため、MT5画面で確認し、必要なら手動決済
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC strategy integrationはまだ触っていない
- GOLD sidecar の実送信はまだしない
```

---

## 現時点の結論

```text
BTC manual demo order_send smoke test は成功。
repeat-send block も sender short-circuit で正常PASS。
次はBTCポジション確認/手動決済、またはBTC manual close smoke test の検討。
```
