# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_COMPACT_CONSOLE_PASS

## 目的

GOLD BUY/SELL multi-strategy sidecar dry-run / guarded demo send flow の minute-aligned loop が、実運用向けに compact console output 化され、1 cycle 確認で PASS した状態を次チャットへ引き継ぐ。

今回の変更により、実運用中のコンソールには巨大な子プロセス stdout を流さず、1 cycle ごとの要約だけを表示する。

詳細ログは従来どおり `command_logs` に保存する。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_ALIGNED_COMPACT_CONSOLE_PASS.md
```

併読推奨:

```text
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

## 今回更新したファイル

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py
```

変更内容:

```text
1. デフォルトのコンソール出力を compact に変更
2. 子BAT/wrapper の stdout/stderr は command_logs に保存
3. コンソールには 1 cycle 要約だけ表示
4. デバッグ時だけ --echo-wrapper-output で従来どおり詳細 stdout/stderr を表示可能
5. loop summary schema を v2 compact console に更新
6. aligned_loop_log.csv に最新M15、same-M15 skip、payload rows、timing などを記録
```

---

## compact console の意図

以前の aligned runner は、子BATの stdout をファイル保存したうえで、コンソールにも丸ごと表示していた。

そのため、標準確認や一回実行のログが非常に長くなり、実運用ループでは見づらい。

今回の変更後は、通常運用では以下だけを出す。

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

詳細調査が必要な場合のみ、`stdout_log` のファイルを開く。

---

## 実行確認済みコマンド

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py --out-dir data\r\aligned_compact_test --max-cycles 1
```

結果:

```text
returncode=0
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

stdout 保存先:

```text
data\r\aligned_compact_test\command_logs\cycle_00001_20260510_043346_stdout.txt
```

summary:

```text
data\r\aligned_compact_test\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json
```

---

## 実行時コンソール例

```json
{
  "cycle_index": 1,
  "cycle_ok": true,
  "latest_m15": "2026-05-08 23:45:00",
  "next_run_utc": "",
  "open_order_intent_count": 0,
  "order_send_called_count": 0,
  "payload_rows_out": 0,
  "reason": "GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_PASS",
  "returncode": 0,
  "router_seconds": 0.0,
  "same_m15_no_signal_skipped": true,
  "sent_rows": 0,
  "signals_found_count": 0,
  "stdout_log": "data\\r\\aligned_compact_test\\command_logs\\cycle_00001_20260510_043346_stdout.txt",
  "summary_json": "data\\r\\aligned_compact_test\\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json",
  "total_seconds": 1.21
}
```

これで、実運用ループ中に巨大ログがコンソールへ流れる問題は解消。

---

## 詳細ログを見たい場合

通常は compact。

詳細をコンソールにも流したい場合だけ以下を使う。

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py --out-dir data\r\aligned_verbose_test --max-cycles 1 --echo-wrapper-output
```

---

## forever aligned BAT について

既存BAT:

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

このBATは以下を呼ぶ。

```text
python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py ^
  --out-dir "%OUT_DIR%" ^
  --max-cycles 0 ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --no-run-immediately
```

`--echo-wrapper-output` は付けていないため、今回の更新後は forever aligned BAT も compact console output で動く。

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

## 次にやること

推奨順:

```text
1. compact console PASS を docs に固定する  ※このファイルで完了
2. scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat を実運用 dry-run で起動
3. コンソールに compact cycle summary だけが毎分表示されることを確認
4. 実CSV signal が出るまでは dry-run のまま待つ
5. signal が出ても、まず no-send / allow-only で payload_rows_out=1 を確認
6. すぐ --send はしない
7. 標準確認 ALL PASS を再確認
8. ユーザー明示承認がある場合のみ armed BAT の設計/作成を検討
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

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
- 実運用ループは compact console output 化済み
- 子プロセスの長い stdout/stderr は command_logs に保存される
- --send 単独では sender に --send が渡らない
- --allow-demo-send 単独でも sender に --send が渡らない
- payload rows 0 fixture で --allow-demo-send --send 相当でも sender に --send が渡らない
- send_flag_passed_to_sender=false
- order_send_called_count=0
- sent_rows=0
- production registry writeなし

今回更新済み:
- scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py
  - compact console output default
  - --echo-wrapper-output 追加
  - aligned_loop_log.csv に追加項目

実行確認済み:
python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py --out-dir data\r\aligned_compact_test --max-cycles 1

結果:
- cycle_ok=true
- reason=GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_PASS
- latest_m15=2026-05-08 23:45:00
- same_m15_no_signal_skipped=true
- signals_found_count=0
- open_order_intent_count=0
- payload_rows_out=0
- order_send_called_count=0
- sent_rows=0
- router_seconds=0.0
- total_seconds=1.21

重要:
- まだ armed / 実送信BAT は作っていない
- まだ実CSV signal で --allow-demo-send --send は実行しない
- まだ MT5 demo order_send はしない
- まだ production registry write は実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC統合はまだ触らない

次にやること:
1. scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat を実運用 dry-run として起動
2. compact cycle summary だけが毎分表示されることを確認
3. 実CSV signal が出るまで dry-run のまま待つ
4. signal が出ても、まず no-send / allow-only で payload_rows_out=1 を確認
5. すぐ --send はしない
6. 標準確認 ALL PASS を再確認
7. ユーザー明示承認がある場合のみ armed BAT の設計/作成を検討
```

---

## 現時点の結論

```text
実運用 dry-run loop のコンソール出力は compact 化済み。
長い詳細ログは command_logs に保存。
次は forever aligned BAT を起動して、signal-present を dry-run で待つ段階。
```
