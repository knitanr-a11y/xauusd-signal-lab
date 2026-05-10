# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ARMED_READY

## 目的

GOLD multi-strategy sidecar guarded demo send flow を、市場再開前にできる範囲で完成扱いまで進めた状態を次チャットへ引き継ぐ。

市場再開後でないと確認できないものは残るが、以下は完了済み。

```text
GOLD sidecar dry-run
signal-present fixture
fixture -> real sender dry-run
GOLD guarded demo send-once armed runner
GOLD guarded armed suppression validation
BTC manual order_send smoke test
GOLD open position read-only preview
GOLD close intent read-only preview
```

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ARMED_READY.md
```

併読推奨:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_DEMO_OPEN_POSITION_CLOSE_INTENT_PREVIEW_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
```

---

## 現在の戦略スロット

### BUY

```text
slot: BUY_C_ENV_RR2_72H
strategy: GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

### SELL

```text
slot: SELL_H1H4_BEAR_AB
strategy: GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

---

## 今回追加/検証した主要ファイル

### GOLD signal-present fixture -> real sender dry-run

```text
scripts/run_gold_multi_strategy_signal_present_sender_dry_run_validation.py
```

実行済み:

```bat
python scripts\run_gold_multi_strategy_signal_present_sender_dry_run_validation.py
```

結果:

```text
validation_ok=true
strict_order_check_ok=true
structural_safe_ok=true
reason=GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_STRICT_PASS
symbol=GOLD#
direction=BUY
lot=0.01
sender_returncode=0
sender_rows_out=1
sender_dry_run_check_ok_rows=1
sender_error_rows=0
sender_order_send_called_count=0
sender_sent_rows=0
order_send_called_count=0
sent_rows=0
```

sender row:

```text
order_status=DRY_RUN_ORDER_CHECK_OK
broker_symbol=GOLD#
direction=BUY
lot=0.01
existing_symbol_positions=1
existing_symbol_lot=0.01
existing_symbol_directions=BUY
current_execution_price=4715.97
sl_price=4695.97
tp_price=4735.97
order_check_ok=true
order_send_called=false
order_send_ok=false
validation_errors=
```

この validation は `--send` を渡していない。

---

### GOLD guarded demo send-once armed runner

```text
scripts/run_gold_multi_strategy_guarded_demo_send_once_armed.py
```

実行済み no-flags:

```bat
python scripts\run_gold_multi_strategy_guarded_demo_send_once_armed.py
```

結果:

```text
cycle_ok=true
reason=GOLD_GUARDED_DEMO_SEND_ONCE_SUPPRESSED_NO_SEND_PASS
mode=SUPPRESSED_NO_SEND_OR_DRY_RUN
allow_demo_send=false
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
sender_invoked=true
sender_order_send_called_count=0
sender_sent_rows=0
sender_dry_run_check_ok_rows=1
production_registry_mutated=false
```

GOLD symbol_info 動的取得確認:

```text
symbol=GOLD#
symbol_digits=2
symbol_point=0.01
symbol_trade_stops_level=0
symbol_volume_min=0.01
symbol_volume_step=0.01
symbol_volume_max=50.0
entry_price_reference=4715.97
sl_price=4695.97
tp_price=4735.97
```

重要:

```text
BTCUSD# の価格桁・point・stops_level はGOLDへ流用していない。
GOLD# の symbol_info / symbol_info_tick から毎回取得する。
```

---

### GOLD guarded demo send-once armed suppression validation

```text
scripts/run_gold_guarded_demo_send_once_armed_suppression_validation.py
```

初回は `as_bool()` の引数ミスで落ちたため修正済み。

修正コミット:

```text
da4c979ab5adb2966e27cfbf6747b6e6675494ad
Fix bool helper default in GOLD armed suppression validation
```

再実行:

```bat
python scripts\run_gold_guarded_demo_send_once_armed_suppression_validation.py
```

結果:

```text
validation_ok=true
reason=GOLD_GUARDED_DEMO_SEND_ONCE_ARMED_SUPPRESSION_VALIDATION_PASS
cases_total=3
cases_failed=0
order_send_called_count=0
sent_rows=0
allow_and_send_case_executed=false
```

cases:

```text
no_flags:
  cycle_ok=true
  send_requested=false
  allow_demo_send=false
  send_flag_passed_to_sender=false
  send_suppressed_reason=SEND_NOT_REQUESTED
  sender_order_send_called_count=0
  sender_sent_rows=0
  sender_dry_run_check_ok_rows=1

send_only:
  cycle_ok=true
  send_requested=true
  allow_demo_send=false
  send_flag_passed_to_sender=false
  send_suppressed_reason=ALLOW_DEMO_SEND_NOT_SET
  sender_order_send_called_count=0
  sender_sent_rows=0
  sender_dry_run_check_ok_rows=1

allow_only:
  cycle_ok=true
  send_requested=false
  allow_demo_send=true
  send_flag_passed_to_sender=false
  send_suppressed_reason=SEND_NOT_REQUESTED
  sender_order_send_called_count=0
  sender_sent_rows=0
  sender_dry_run_check_ok_rows=1
```

重要:

```text
--allow-demo-send --send の実送信ケースはこのvalidationでは実行していない。
```

---

## BTC manual smoke test 到達点

BTCは市場が開いているため、manual smoke test として実注文経路を確認済み。

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

BTC send-once では `order_send_retcode=10009 / Request executed` まで確認済み。

ただしこれは GOLD strategy signal ではない。

---

## GOLD open position / close intent preview 到達点

GOLD持ち越しポジション read-only preview:

```bat
python scripts\show_gold_demo_open_positions_preview.py
```

結果:

```text
preview_ok=true
positions_count=1
directions={"BUY": 1}
total_volume=0.01
total_profit=-1983.0
order_send_called_count=0
close_executed_count=0
```

GOLD close intent read-only preview:

```bat
python scripts\show_gold_demo_close_intent_preview.py
```

結果:

```text
preview_ok=true
positions_count=1
close_intent_rows=1
directions={"BUY": 1}
close_directions={"SELL": 1}
total_volume=0.01
total_profit=-1983.0
order_send_called_count=0
close_executed_count=0
```

解釈:

```text
現在GOLD BUY 0.01が1件ある。
閉じるならSELL 0.01が必要。
ただし市場停止中なので、自動決済はまだしない。
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
fixture -> real sender dry-run: PASS
GOLD guarded demo send-once armed runner: PASS no-send
GOLD guarded armed suppression validation: PASS
GOLD symbol_info dynamic precision handling: PASS
order_send_called_count=0 in GOLD validations
sent_rows=0 in GOLD validations
production registry writeなし
```

---

## 今日中完成ライン

今日中に完成扱いにできる範囲:

```text
GOLD multi-strategy sidecar guarded demo send flow の実装・dry-run・fixture・sender連携・抑止validationは完了。
BTCで共通senderの実order_send経路も検証済み。
GOLD側は市場再開後の実CSV signal / 実GOLD約定確認だけ残る。
```

市場再開後でないとできないこと:

```text
GOLD latest_m15 の実更新確認
実CSV GOLD signal 発生確認
実CSV signal 由来 payload_rows_out>=1 確認
GOLD demo order_send の約定確認
GOLD close execution 確認
```

---

## まだやらないこと

```text
Gold持ち越しポジションの自動決済
GOLD MT5 demo order_send
GOLD --allow-demo-send --send 実行
send成功後の production registry write
close intent MT5 execution
BTC strategy integration
既存 Mochipoyo 本体BATへの統合
既存 Mochipoyo 本体 ledgers / trigger-state mutation
production position_registry.csv write
```

---

## 市場再開後の最短手順

1. GOLD sidecar aligned dry-run を起動。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.ps1
```

2. latest_m15 更新または signal 出現を見る。

```text
latest_m15 が更新
signals_found_count >= 1
payload_rows_out >= 1
```

3. signal が出たら停止。

```text
Ctrl+C
```

4. status viewer。

```bat
scripts\show_gold_multi_strategy_aligned_dry_run_status.bat
```

5. まだ即送信しない。no-send / allow-only / suppression validation / standard validation を確認。

6. 実送信へ進む場合でも、以下を再確認。

```text
GOLD既存ポジション
position_policy
max_symbol_positions
max_symbol_lot
SL/TP
symbol_digits / point / stops_level
expected-login
require-demo-account
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ARMED_READY.md
docs/NEXT_CHAT_HANDOFF_GOLD_DEMO_OPEN_POSITION_CLOSE_INTENT_PREVIEW_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_CLOSE_PREVIEW_ZERO_POSITION_PASS.md
docs/NEXT_CHAT_HANDOFF_BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md

現在は、GOLDのBUY/SELL multi-strategyを既存もちぽよ本体に直接混ぜず、独立したsidecar dry-run / guarded demo send flowとして構築中です。

今日中にできる完成ラインとして、以下までPASS済みです。
- GOLD sidecar dry-run
- signal-present fixture validation
- payload_rows=1 guarded gate validation
- GOLD fixture -> real sender dry-run validation
- GOLD guarded demo send-once armed runner no-send
- GOLD guarded armed suppression validation
- GOLD symbol_info dynamic precision handling
- BTC manual demo order_send smoke test
- BTC repeat-send block
- BTC close preview zero position
- GOLD open position read-only preview
- GOLD close intent read-only preview

追加済み:
- scripts/run_gold_multi_strategy_signal_present_sender_dry_run_validation.py
- scripts/run_gold_multi_strategy_guarded_demo_send_once_armed.py
- scripts/run_gold_guarded_demo_send_once_armed_suppression_validation.py
- docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ARMED_READY.md

直近実行結果:
python scripts\run_gold_multi_strategy_signal_present_sender_dry_run_validation.py
- validation_ok=true
- reason=GOLD_SIGNAL_PRESENT_SENDER_DRY_RUN_STRICT_PASS
- sender_dry_run_check_ok_rows=1
- sender_order_send_called_count=0
- sender_sent_rows=0

python scripts\run_gold_multi_strategy_guarded_demo_send_once_armed.py
- cycle_ok=true
- reason=GOLD_GUARDED_DEMO_SEND_ONCE_SUPPRESSED_NO_SEND_PASS
- send_flag_passed_to_sender=false
- sender_order_send_called_count=0
- sender_sent_rows=0
- symbol=GOLD#
- symbol_digits=2
- symbol_point=0.01
- symbol_volume_min=0.01
- symbol_volume_step=0.01

python scripts\run_gold_guarded_demo_send_once_armed_suppression_validation.py
- validation_ok=true
- cases_total=3
- cases_failed=0
- order_send_called_count=0
- sent_rows=0
- allow_and_send_case_executed=false

重要:
- BTCで共通senderの実order_send経路は検証済み
- GOLD側は市場再開後の実CSV signal / 実GOLD約定確認だけ残る
- GOLD価格桁はBTCから流用せず、GOLD# symbol_infoから取得済み
- 現在GOLD BUY 0.01の持ち越しポジションあり
- Gold持ち越しポジションの自動決済はまだしない
- GOLD --allow-demo-send --send はまだ実行しない
- production registry writeはまだ実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC strategy integrationはまだ触らない

市場再開後はGOLD sidecar aligned dry-runを起動し、latest_m15更新またはpayload_rows_out>=1を確認する。
```

---

## 現時点の結論

```text
GOLD multi-strategy sidecar guarded demo send flow は、市場再開前にできる実装・dry-run・fixture・sender連携・抑止validationまで完了。
残るのは市場再開後の実CSV signal確認と実GOLD約定確認のみ。
```
