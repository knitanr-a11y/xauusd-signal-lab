# NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS

## 目的

BTC manual demo order_send smoke test 後に、BTCUSD# の手動close previewを実行し、現在BTCポジションが残っていないことを確認した状態を次チャットへ引き継ぐ。

これは GOLD multi-strategy signal ではない。

これは BTC strategy integration でもない。

これは **MT5 demo order_send 経路の手動 smoke test 後のBTCポジション確認**。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS.md
```

併読推奨:

```text
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
```

---

## 関連ファイル

BTC no-send / order_check runner:

```text
scripts/run_btc_manual_demo_order_send_smoke_test.py
```

BTC send-once guarded runner:

```text
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
```

BTC close preview runner:

```text
scripts/run_btc_manual_demo_close_smoke_test_preview.py
```

---

## BTC manual close preview の位置づけ

```text
目的: BTCUSD# の現在ポジションを読み取り、close-intent previewを作る
対象: BTCUSD#
口座: XMTrading demo login 75539039
実決済: しない
order_send: しない
production registry write: なし
GOLD strategy signal: 不使用
BTC strategy integration: 不使用
```

---

## 実行コマンド

```bat
python scripts\run_btc_manual_demo_close_smoke_test_preview.py
```

---

## 実行結果

```text
preview_ok=true
reason=BTC_MANUAL_DEMO_CLOSE_SMOKE_TEST_PREVIEW_PASS
symbol=BTCUSD#
positions_total_for_symbol=0
positions_matched=0
matched_total_volume=0
matched_total_profit=0
close_intent_rows=0
order_send_called_count=0
close_executed_count=0
```

出力:

```text
data\r\btc_manual_demo_close_smoke_test_preview\btc_manual_positions_preview.csv
data\r\btc_manual_demo_close_smoke_test_preview\btc_manual_close_intents_preview.csv
data\r\btc_manual_demo_close_smoke_test_preview\latest_btc_manual_demo_close_smoke_test_preview_result.json
```

---

## 解釈

BTCUSD# は現在ポジションなし。

```text
BTC close preview はPASS
BTC manual close smoke test の実決済ステップは不要
BTC send-once repeat block もPASS済み
```

ユーザー確認:

```text
ポジションは持ち越しているGoldだけ
```

---

## 現在のBTC manual smoke test 到達点

```text
BTC no-send / order_check smoke test: PASS
BTC send-once guarded runner: PASS
BTC demo order_send: PASS
repeat-send marker: written
repeat-send block: PASS
repeat-send short-circuit before sender: PASS
BTC close preview: PASS
BTCUSD# current positions: 0
production registry writeなし
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

## まだやらないこと

```text
Gold持ち越しポジションの自動決済
GOLD MT5 demo order_send
GOLD armed BAT
send成功後の production registry write
close intent MT5 execution
BTC strategy integration
既存 Mochipoyo 本体BATへの統合
```

---

## 次にやること候補

```text
1. GOLD sidecar aligned dry-run に戻る
2. 実CSV GOLD signal が出るまで待つ
3. signal が出たら status viewer / no-send / allow-only / 標準確認ALL PASS を確認
4. すぐGOLD実送信はしない
```

または、現在持ち越しているGoldポジションを確認するだけの read-only preview を作る。

```text
GOLD open position read-only preview
order_sendなし
closeなし
production registry writeなし
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_NO_SEND_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md

BTC manual demo order_send smoke test として、BTCUSD# BUY 0.01 の demo send-once は成功済みです。
その後、success marker による repeat-send block もPASSし、repeat block時は sender_invoked=false で追加注文なしです。

BTC close preview 実行:
python scripts\run_btc_manual_demo_close_smoke_test_preview.py

結果:
- preview_ok=true
- positions_total_for_symbol=0
- positions_matched=0
- close_intent_rows=0
- order_send_called_count=0
- close_executed_count=0

現在BTCUSD#ポジションはありません。
ユーザー確認では、ポジションは持ち越しているGoldだけです。

重要:
- GOLD sidecar の実送信はまだしない
- Gold持ち越しポジションの自動決済はしない
- production registry write はまだ実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC strategy integrationはまだ触らない

次にやること:
1. GOLD sidecar aligned dry-run に戻る
2. 実CSV GOLD signal を待つ
3. signal が出たら no-send / allow-only / status viewer / 標準確認ALL PASS を確認
4. またはGold持ち越しポジションのread-only previewだけ作る
```

---

## 現時点の結論

```text
BTC manual smoke test 系は完了。
BTCポジションは残っていない。
次はGOLD sidecar dry-runへ戻る段階。
```
