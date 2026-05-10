# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS

## 目的

GOLD BUY/SELL multi-strategy sidecar dry-run / guarded demo send flow で、実シグナルを待たずに `payload_rows=1` の signal-present 状態を fixture で検証し、PASS した状態を次チャットへ引き継ぐ。

現在も、既存 Mochipoyo 本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として構築中。

今回の到達点は以下。

```text
1. 実CSV signal はまだ出ていない
2. しかし signal-present fixture により payload_rows=1 状態の guarded gate を検証済み
3. no flags / --send only / --allow-demo-send only の抑止 PASS
4. --allow-demo-send --send 相当では gate eligibility が true になることを確認
5. ただし sender / MT5 / order_check / order_send は一切呼んでいない
6. order_send_called_count=0 / sent_rows=0 / production registry writeなし
```

まだ `--allow-demo-send --send` を含む armed / 実送信BAT は作っていない。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
```

併読推奨:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_COMPACT_CONSOLE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_WRAPPER.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_FOREVER_ALIGNED_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_SAME_M15_SKIP.md
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

## 今回追加した validation

```text
scripts/run_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation.py
```

目的:

```text
実シグナルを待たずに payload_rows=1 の状態を人工的に作り、guarded demo-send gate の挙動を確認する。
```

この validation は以下をしない。

```text
live scan しない
sender を呼ばない
MetaTrader5 を初期化しない
order_check しない
order_send しない
production registry を書かない
BTC注文テストもしない
```

---

## 実行コマンド

```bat
python scripts\run_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation.py
```

出力先:

```text
data\r\gds_signal_present_fixture
```

summary:

```text
data\r\gds_signal_present_fixture\latest_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation_result.json
```

case log:

```text
data\r\gds_signal_present_fixture\signal_present_fixture_case_log.csv
```

fixture payload:

```text
data\r\gds_signal_present_fixture\fixture_order_payloads_signal_present.csv
```

---

## validation cases

```text
Case 1: payload_present_no_flags
  payload_rows=1
  send_requested=false
  allow_demo_send=false
  expected_pass_send=false
  expected_reason=SEND_NOT_REQUESTED

Case 2: payload_present_send_only
  payload_rows=1
  send_requested=true
  allow_demo_send=false
  expected_pass_send=false
  expected_reason=ALLOW_DEMO_SEND_NOT_SET

Case 3: payload_present_allow_only
  payload_rows=1
  send_requested=false
  allow_demo_send=true
  expected_pass_send=false
  expected_reason=SEND_NOT_REQUESTED

Case 4: payload_present_allow_and_send_eligibility_preview
  payload_rows=1
  send_requested=true
  allow_demo_send=true
  expected_pass_send=true
  expected_reason=""
```

重要:

```text
Case 4 は eligibility preview のみ。
「両フラグ + payload_rows=1 なら gate が開く」ことだけ確認する。
実際には sender / MT5 / order_send は呼ばない。
```

---

## 実行結果

実行:

```bat
python scripts\run_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation.py
```

結果:

```text
validation_ok=true
reason=SIGNAL_PRESENT_FIXTURE_VALIDATION_PASS
checks_total=4
checks_failed=0
```

安全確認:

```text
live_scan_ran=false
sender_invoked=false
mt5_initialized=false
order_check_called=false
order_send_called_count=0
sent_rows=0
production_registry_mutated=false
existing_mochipoyo_bat_modified=false
existing_mochipoyo_ledgers_mutated=false
trigger_state_mutated=false
btc_order_smoke_test_performed=false
```

---

## BTC注文について

ユーザーから以下の意向あり。

```text
Gold市場が止まっているため、注文を出すならBTCの方で進めたい。
```

ただし今回の validation では BTC order smoke test はまだ実施していない。

理由:

```text
GOLD multi-strategy sidecar fixture は、GOLD戦略シグナルの guarded gate 検証。
BTC注文は strategy signal ではなく MT5 order_send 接続テストになるため、別枠で作るべき。
```

次にやるなら、名前も明確に分ける。

```text
BTC manual demo order_send smoke test
```

これは GOLD sidecar / strategy signal / production registry write と混ぜない。

---

## 現在の到達点

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
--send 単独の抑止: PASS
--allow-demo-send 単独の抑止: PASS
payload rows 0 fixtureでの --allow-demo-send --send 抑止: PASS
payload rows 1 fixtureでの --allow-demo-send --send eligibility preview: PASS
send_flag_passed_to_sender=false in all no-send/suppressed cases
order_send_called_count=0
sent_rows=0
production registry writeなし
```

---

## まだ作っていないもの / まだやらないこと

以下はまだ作っていない。

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_armed.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_demo_send_and_send.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_send.bat
scripts/run_btc_manual_demo_order_send_smoke_test.py
scripts/run_btc_manual_demo_order_send_smoke_test.bat
```

以下はまだ実施しない。

```text
実CSV GOLD signal あり状態での --allow-demo-send --send 実行
GOLD MT5 demo order_send
BTC MT5 demo order_send
send成功後の production registry write
close intent MT5 execution
BTC strategy integration
既存 Mochipoyo 本体BATへの統合
```

特に以下はまだ実行しない。

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py --allow-demo-send --send
```

---

## 現在守る安全境界

以下は引き続き触らない。

```text
既存 Mochipoyo 本体BAT
既存 ledgers
既存 trigger-state files
production position_registry.csv
close intent MT5 execution
BTC統合
```

---

## 次に進む場合の選択肢

### A. 安全側を継続

```text
PowerShell launcher で aligned dry-run を継続運用し、実CSV GOLD signal を待つ。
```

### B. GOLD実シグナル待ちをさらに飛ばす

```text
fixture payload を sender dry-run に実際に通す validation を作る。
ただし --send は付けない。
MT5 order_check までは呼ばれる可能性があるため、仕様確認が必要。
```

### C. BTC manual demo order_send smoke test へ進む

```text
GOLD市場が閉じているため、実注文テストはBTCで行う。
ただしこれはGOLD strategy signalではなく、MT5 order_send接続の手動smoke test。
明示的に別ファイル・別出力先・別ledger・別magic・max-orders=1・最小lot・demo account guard必須で作る。
```

---

## BTC manual smoke test を作る場合の安全条件

```text
既存GOLD sidecarとは別ファイル
既存Mochipoyo本体とは別ファイル
既存ledgersとは別ledger
production position_registry.csv writeなし
require-demo-account 必須
expected-login 必須
max-orders=1
position-policy=block_any
最小lot固定
BTC broker symbol はユーザー実環境で確認してから固定
市場価格から安全なSL/TPを計算
まず --send なし dry-run / order_check まで
その後、ユーザー明示承認がある場合のみ --send あり
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
docs/GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_COMPACT_CONSOLE_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_WRAPPER.md
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_FOREVER_ALIGNED_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_SAME_M15_SKIP.md

現在は、GOLDのBUY/SELL multi-strategyを既存もちぽよ本体に直接混ぜず、独立したsidecar dry-run / guarded demo send flowとして構築中です。

現在の戦略スロット:
- BUY_C_ENV_RR2_72H
  - GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
- SELL_H1H4_BEAR_AB
  - GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H

到達点:
- Case Matrix PASS
- Monitor skip A/B PASS
- Same-M15 no-signal skip A/B PASS
- Guarded demo-send safety validation PASS
- 標準確認 scripts\run_gold_multi_strategy_case_matrix_validation.bat は ALL PASS
- sidecar dry-run単発 PASS
- forever aligned dry-run PASS
- 毎分02秒起動 OK
- no-send BAT PASS
- allow-only BAT PASS
- aligned compact console 1-cycle PASS
- aligned forever .bat launcher PASS
- aligned status viewer PASS
- aligned PowerShell launcher PASS
- Ctrl+C graceful stop PASS
- pre-cycle Ctrl+C summary preservation PASS
- status viewer fallback recovery PASS
- final status viewer summary_json recovery PASS
- signal-present fixture validation PASS
- payload_rows=1 guarded gate validation PASS
- --send 単独では sender に --send が渡らない
- --allow-demo-send 単独でも sender に --send が渡らない
- payload rows 0 fixture で --allow-demo-send --send 相当でも sender に --send が渡らない
- payload rows 1 fixture で --allow-demo-send --send 相当なら gate eligibility は true
- ただし sender / MT5 / order_send は呼んでいない
- send_flag_passed_to_sender=false in all no-send/suppressed cases
- order_send_called_count=0
- sent_rows=0
- production registry writeなし

今回追加済み:
- scripts/run_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation.py
- docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SIGNAL_PRESENT_FIXTURE_PASS.md

実行確認済み:
python scripts\run_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation.py

結果:
- validation_ok=true
- reason=SIGNAL_PRESENT_FIXTURE_VALIDATION_PASS
- checks_total=4
- checks_failed=0
- live_scan_ran=false
- sender_invoked=false
- mt5_initialized=false
- order_check_called=false
- order_send_called_count=0
- sent_rows=0
- production_registry_mutated=false
- btc_order_smoke_test_performed=false

重要:
- まだ armed / 実送信BAT は作っていない
- まだ実CSV GOLD signal で --allow-demo-send --send は実行しない
- まだ GOLD MT5 demo order_send はしない
- まだ BTC MT5 demo order_send はしない
- BTCで注文テストするなら、GOLD strategyとは別枠の manual demo order_send smoke test として作る
- まだ production registry write は実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC統合はまだ触らない

次にやること候補:
1. 安全側継続: PowerShell launcher で aligned dry-run を継続し、実CSV GOLD signal を待つ
2. さらに進める: fixture payload を sender dry-run に実際に通す validation を作る。ただし --send なし
3. 注文接続テストへ進める: BTC manual demo order_send smoke test を別枠で設計する
```

---

## 現時点の結論

```text
実シグナルを待たずに、payload_rows=1 の guarded gate までは安全に検証済み。
次に実注文テストをするなら、GOLD戦略とは分けて BTC manual demo order_send smoke test として設計する。
実送信はまだしていない。
```
