# NEXT_CHAT_HANDOFF_GOLD_DEMO_OPEN_POSITION_CLOSE_INTENT_PREVIEW_PASS

## 目的

GOLD持ち越しポジションの read-only preview と close intent preview が PASS した状態を次チャットへ引き継ぐ。

これは GOLD multi-strategy signal の実注文ではない。

これは close intent MT5 execution ではない。

これは **現在のGOLDデモ口座ポジション確認と、決済するなら必要な反対方向のread-only preview**。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_DEMO_OPEN_POSITION_CLOSE_INTENT_PREVIEW_PASS.md
```

併読推奨:

```text
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
```

---

## 関連ファイル

GOLD open positions read-only preview:

```text
scripts/show_gold_demo_open_positions_preview.py
```

GOLD close intent read-only preview:

```text
scripts/show_gold_demo_close_intent_preview.py
```

どちらも以下はしない。

```text
order_sendしない
決済しない
production registryを書かない
既存Mochipoyo本体/ledger/trigger-stateを触らない
```

---

## GOLD open positions preview 実行結果

実行:

```bat
python scripts\show_gold_demo_open_positions_preview.py
```

結果:

```text
preview_ok=true
reason=GOLD_DEMO_OPEN_POSITIONS_PREVIEW_PASS
positions_count=1
directions={"BUY": 1}
total_volume=0.01
total_profit=-1983.0
order_send_called_count=0
close_executed_count=0
```

出力:

```text
data\r\gold_demo_open_positions_preview\gold_demo_open_positions_preview.csv
data\r\gold_demo_open_positions_preview\latest_gold_demo_open_positions_preview_result.json
```

---

## GOLD close intent preview 実行結果

実行:

```bat
python scripts\show_gold_demo_close_intent_preview.py
```

結果:

```text
preview_ok=true
reason=GOLD_DEMO_CLOSE_INTENT_PREVIEW_PASS
positions_count=1
close_intent_rows=1
directions={"BUY": 1}
close_directions={"SELL": 1}
total_volume=0.01
total_profit=-1983.0
order_send_called_count=0
close_executed_count=0
```

出力:

```text
data\r\gold_demo_close_intent_preview\gold_demo_close_preview_positions.csv
data\r\gold_demo_close_intent_preview\gold_demo_close_intents_preview.csv
data\r\gold_demo_close_intent_preview\latest_gold_demo_close_intent_preview_result.json
```

---

## 解釈

現在のGOLDデモ口座ポジション:

```text
GOLD系シンボルのBUY 0.01が1件
評価損: -1983.0
```

決済する場合の方向:

```text
close_direction=SELL
volume=0.01
```

ただし、これは read-only preview であり、まだ自動決済はしていない。

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

早く進めるなら選択肢は以下。

### A. GOLD sidecar aligned dry-run に戻る

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.ps1
```

市場再開後に latest_m15 更新 / 実CSV signal を待つ。

### B. GOLD manual close smoke test を作る

```text
現在のGOLD BUY 0.01を閉じるための guarded close runner を作る。
ただし、これは close intent MT5 execution になるため、ユーザー明示承認が必要。
```

### C. GOLD sidecar production registry preview 設計へ進む

```text
実送信後に production registry へどう書くかを preview だけ設計する。
まだproduction registryは書かない。
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

docs/NEXT_CHAT_HANDOFF_GOLD_DEMO_OPEN_POSITION_CLOSE_INTENT_PREVIEW_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md

GOLD持ち越しポジションのread-only previewとclose intent previewはPASS済みです。

実行済み:
python scripts\show_gold_demo_open_positions_preview.py
python scripts\show_gold_demo_close_intent_preview.py

結果:
- positions_count=1
- directions={"BUY": 1}
- close_directions={"SELL": 1}
- total_volume=0.01
- total_profit=-1983.0
- close_intent_rows=1
- order_send_called_count=0
- close_executed_count=0

重要:
- まだGold持ち越しポジションは自動決済していない
- まだGOLD MT5 demo order_sendはしない
- まだproduction registry writeは実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC strategy integrationはまだ触らない

次にやること候補:
1. GOLD sidecar aligned dry-runへ戻る
2. ユーザー明示承認があればGOLD manual close smoke testを作る
3. production registry preview設計だけ進める
```

---

## 現時点の結論

```text
GOLD持ち越しポジションは BUY 0.01 が1件。
closeするなら SELL 0.01 が必要。
ただし、まだ自動決済はしていない。
```
