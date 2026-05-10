# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY

## 目的

GOLD BUY/SELL multi-strategy sidecar dry-run / guarded demo send flow が、実運用 dry-run loop として起動・停止・状態確認できる段階まで到達した状態を次チャットへ引き継ぐ。

現在も、既存 Mochipoyo 本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として構築中。

今回の最終到達点は以下。

```text
1. aligned dry-run loop compact console output: PASS
2. .bat launcher graceful Python stop: PASS
3. .ps1 PowerShell launcher: PASS
4. status viewer: PASS
5. pre-cycle Ctrl+C summary preservation: PASS
6. aligned_loop_log.csv fallback recovery: PASS
7. aligned_loop_log.csv header schema rotation: implemented
8. final status viewer recovery from summary_json: PASS
9. 実送信なし / order_sendなし / production registry writeなし
```

まだ `--allow-demo-send --send` を含む armed / 実送信BAT は作っていない。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_READY.md
```

併読推奨:

```text
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

## 実運用 dry-run 起動方法

### 推奨: PowerShell launcher

ExecutionPolicy を一時的に Bypass して起動する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.ps1
```

理由:

```text
.bat launcher でも動作するが、Ctrl+C 停止後に Windows cmd.exe 側で
「バッチ ジョブを終了しますか (Y/N)?」が出る場合がある。
PowerShell launcher は Python runner を直接呼ぶため、この batch job 確認が出にくい。
```

### 従来の .bat launcher

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

これも使用可能。

Ctrl+C 後に以下が出たら `y` で終了。

```text
バッチ ジョブを終了しますか (Y/N)?
```

---

## 実運用 dry-run の動作

対象 runner:

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py
```

設定:

```text
max-cycles=0
interval-minutes=1
offset-seconds=2
no-run-immediately=true
console_output=COMPACT
```

動作:

```text
毎分02秒に起動
最新確定M15を評価
same-M15 no-signal skip が有効
子プロセスの長い stdout/stderr は command_logs に保存
コンソールには compact cycle summary だけ表示
```

---

## compact console 表示

1 cycle ごとに以下のみ表示。

```text
cycle_index
cycle_ok
returncode
reason
latest_m15
same_m15_no_signal_skipped
signals_found_count
open_order_intent_count
payload_rows_out
order_send_called_count
sent_rows
router_seconds
total_seconds
next_run_utc
stdout_log
summary_json
```

詳細ログ保存先:

```text
data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\command_logs\*.txt
```

summary:

```text
data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json
```

loop CSV:

```text
data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\aligned_loop_log.csv
```

---

## 状態確認方法

read-only status viewer:

```bat
scripts\show_gold_multi_strategy_aligned_dry_run_status.bat
```

または直接 Python:

```bat
python scripts\show_gold_multi_strategy_aligned_dry_run_status.py
```

確認する値:

```text
status_ok=true
status_source=summary_json
loop_ok=true
last_cycle_ok=true
failed_cycles=0
payload_rows_out=0 または signal時は 1以上
order_send_called_count=0
sent_rows=0
```

`status_source=aligned_loop_log_csv_fallback` が出た場合は、summary_json に有効な last_cycle がないため、aligned_loop_log.csv の最新有効行から復元している状態。

---

## 実行確認済み 1: compact 1-cycle

コマンド:

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py --out-dir data\r\aligned_compact_test --max-cycles 1
```

結果:

```text
cycle_ok=true
reason=GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_PASS
latest_m15=2026-05-08 23:45:00
same_m15_no_signal_skipped=true
signals_found_count=0
open_order_intent_count=0
payload_rows_out=0
order_send_called_count=0
sent_rows=0
router_seconds=0.0
total_seconds=1.21
```

---

## 実行確認済み 2: .bat launcher 起動/停止

コマンド:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

1 cycle 実行結果:

```text
cycle_ok=true
latest_m15=2026-05-08 23:45:00
same_m15_no_signal_skipped=true
signals_found_count=0
open_order_intent_count=0
payload_rows_out=0
order_send_called_count=0
sent_rows=0
router_seconds=0.0
total_seconds=1.146
```

Ctrl+C 停止時:

```text
[STOP] Ctrl+C received. GOLD aligned dry-run loop stopped gracefully.
cycles_run=1 failed_cycles=0
No --send was passed by this runner. No production registry write was performed by this runner.
```

その後 cmd.exe 側で以下が出る場合あり。

```text
バッチ ジョブを終了しますか (Y/N)?
```

これは異常ではない。`y` で終了。

---

## 実行確認済み 3: PowerShell launcher

最初に直接 `.ps1` を実行した場合、PowerShell execution policy でブロックされた。

```text
このシステムではスクリプトの実行が無効になっているため...
PSSecurityException / UnauthorizedAccess
```

これは異常ではない。

一時 Bypass で実行した。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.ps1
```

結果:

```text
PowerShell launcher 起動 OK
Stop with Ctrl+C (graceful, no traceback)
Ctrl+C 停止 OK
[STOP] Ctrl+C received. GOLD aligned dry-run loop stopped gracefully.
cycles_run=0 failed_cycles=0
No --send was passed by this runner. No production registry write was performed by this runner.
```

1 cycle 前に停止したため cycles_run=0 だが、停止処理は正常。

---

## 実行確認済み 4: pre-cycle Ctrl+C summary preservation

PowerShell launcher を1サイクル前に停止した際、以前は `latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json` が `cycles_run=0` summary で上書きされ、status viewer が false になった。

修正後は、1サイクル前に Ctrl+C された場合は latest summary を上書きしない。

代わりに以下へ stop marker を書く。

```text
data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_stop_marker.json
```

表示:

```text
No cycle completed in this session; previous latest operational summary was preserved.
summary_json_preserved=data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json
```

---

## 実行確認済み 5: status viewer fallback recovery

過去に残った `cycles_run=0` summary に対し、status viewer が `aligned_loop_log.csv` の最新有効行から復元できることを確認。

結果:

```text
status_ok=true
status_source=aligned_loop_log_csv_fallback
last_cycle_ok=true
payload_rows_out=0
order_send_called_count=0
sent_rows=0
```

その後、1-cycle を再実行して summary_json を正常化した。

---

## 実行確認済み 6: final status viewer from summary_json

コマンド:

```bat
scripts\show_gold_multi_strategy_aligned_dry_run_status.bat
```

最終結果:

```text
status_ok=true
status_source=summary_json
loop_ok=true
cycles_run=1
failed_cycles=0
last_cycle_index=1
last_cycle_ok=true
last_cycle_end_utc=2026-05-10 04:49:04
latest_m15=2026-05-08 23:45:00
same_m15_no_signal_skipped=true
same_m15_skip_reason=SKIPPED_SAME_CONFIRMED_M15_PREVIOUS_NO_SIGNAL_NO_OPEN_SIGNALS
signals_found_count=0
open_order_intent_count=0
close_intent_count=0
payload_rows_out=0
valid_order_payloads=0
order_send_called_count=0
sent_rows=0
stdout_log=data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\command_logs\cycle_00001_20260510_044902_stdout.txt
```

---

## latest CSV / signal 状態

今回の確認時点では no-signal。

```text
latest_m15=2026-05-08 23:45:00
signals_found_count=0
open_order_intent_count=0
close_intent_count=0
payload_rows_out=0
valid_order_payloads=0
```

same-M15 no-signal skip が有効。

```text
same_m15_no_signal_skipped=true
same_m15_skip_reason=SKIPPED_SAME_CONFIRMED_M15_PREVIOUS_NO_SIGNAL_NO_OPEN_SIGNALS
router_seconds=0.0
total_seconds around 1.1 to 1.2 seconds
```

---

## 実装修正コミット

aligned dry-run / status viewer の安定化で以下を追加済み。

```text
b17d6b5bc257bb1d506e1706f692d0cda8f75d56
Handle aligned dry-run Ctrl-C gracefully

5da948f5e22cf37602c18f72344d7b348dc60532
Add PowerShell aligned dry-run launcher

71b99f9bd9cfdab4cae82877e6213aa23bd16182
Preserve aligned dry-run summary when stopped before first cycle

c2c32aee62c7f335f81293b69939b18eb5b99ed5
Fallback aligned status viewer to latest loop CSV row

c41f62eb10ebf15ffe136109ed7384c03dfbbd7e
Rotate aligned loop CSV when header schema changes
```

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
--send 単独の抑止: PASS
--allow-demo-send 単独の抑止: PASS
payload rows 0 fixtureでの --allow-demo-send --send 抑止: PASS
send_flag_passed_to_sender=false
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
```

以下はまだ実施しない。

```text
実CSV signal あり状態での --allow-demo-send --send 実行
MT5 demo order_send
send成功後の production registry write
close intent MT5 execution
BTC integration
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

## signal が出た場合の手順

signal が出ると以下が 1 以上になる可能性がある。

```text
signals_found_count
open_order_intent_count
payload_rows_out
valid_order_payloads
```

その場合もすぐ `--send` しない。

手順:

```text
1. forever aligned dry-run を Ctrl+C で停止
2. status viewer の出力を保存
3. stdout_log と summary_json を保存
4. 標準確認BATを再実行して ALL PASS を確認
5. no-send BAT / allow-only BAT で payload_rows_out を再確認
6. ユーザー明示承認がある場合のみ armed BAT の設計/作成を検討
7. demo send 後も production registry write は別段階
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

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
- 実運用ループは compact console output 化済み
- 子プロセスの長い stdout/stderr は command_logs に保存される
- --send 単独では sender に --send が渡らない
- --allow-demo-send 単独でも sender に --send が渡らない
- payload rows 0 fixture で --allow-demo-send --send 相当でも sender に --send が渡らない
- send_flag_passed_to_sender=false
- order_send_called_count=0
- sent_rows=0
- production registry writeなし

実運用dry-run起動:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.ps1

状態確認:
scripts\show_gold_multi_strategy_aligned_dry_run_status.bat

最終 status viewer 結果:
- status_ok=true
- status_source=summary_json
- latest_m15=2026-05-08 23:45:00
- same_m15_no_signal_skipped=true
- payload_rows_out=0
- order_send_called_count=0
- sent_rows=0

重要:
- まだ armed / 実送信BAT は作っていない
- まだ実CSV signal で --allow-demo-send --send は実行しない
- まだ MT5 demo order_send はしない
- まだ production registry write は実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC統合はまだ触らない

次にやること:
1. PowerShell launcher で aligned dry-run を継続運用
2. 実CSV signal が出るまで dry-run のまま待つ
3. signal が出たら、まず status viewer / no-send / allow-only で payload_rows_out=1 を確認
4. すぐ --send はしない
5. 標準確認 ALL PASS を再確認
6. ユーザー明示承認がある場合のみ armed BAT の設計/作成を検討
```

---

## 現時点の結論

```text
GOLD multi-strategy sidecar は、実運用 dry-run loop として起動・停止・状態確認まで準備完了。
status viewer も summary_json から正常復帰済み。
次は PowerShell launcher で compact dry-run を継続し、signal-present 状態を待つ段階。
実送信はまだしない。
```
