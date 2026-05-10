# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_WRAPPER

## 目的

GOLD BUY/SELL multi-strategy sidecar flow の現在地点を次チャットへ引き継ぐ。

現在は、既存 Mochipoyo 本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として構築中。

今回の到達点は、軽量化済み sidecar dry-run を維持したまま、guarded demo send once wrapper を追加し、`--send` 単独では sender に `--send` が渡らないことを確認した段階。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_WRAPPER.md
```

併読推奨:

```text
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_FOREVER_ALIGNED_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_SAME_M15_SKIP.md
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
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

## 現在の標準確認コマンド

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

このBATは以下を一括で検証する。

```text
1. Case Matrix 4ケース
2. monitor skip A/B invariance
3. same-M15 no-signal skip A/B invariance
```

期待値:

```text
GOLD standard validation ALL PASS
```

最新状態では PASS 済み。

---

## 軽量化到達点

### monitor skip

有効フラグ:

```text
--skip-monitor-when-no-open-signals
```

意味:

```text
live_scan は通常通り実行
signal_found / signal_key / scan_reason / latest_m15_close_time は通常通り決める
未解決 dry-run signal がない時だけ position_monitor を skip
```

A/B確認済み:

```text
validation_ok=true
reason=MONITOR_SKIP_SIGNAL_INVARIANCE_PASS
checks_failed=[]
```

### same-M15 no-signal skip

有効フラグ:

```text
--skip-same-m15-no-signal
```

意味:

```text
毎分02秒 loop は維持
同じ latest confirmed M15 で前回 no-signal / no-intent / no-unresolved だった時だけ router scan を skip
M15が変われば通常scanに戻る
signalが出た場合も skip 条件から外れる
```

A/B確認済み:

```text
validation_ok=true
reason=SAME_M15_NO_SIGNAL_SKIP_INVARIANCE_PASS
checks_failed=[]
```

速度例:

```text
router_seconds=0.0
total_seconds=約1.2〜1.3秒
```

---

## forever aligned dry-run 到達点

実行コマンド:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

確認済み:

```text
毎分02秒起動: OK
CYCLE 1: returncode=0 / cycle_ok=true
CYCLE 2: returncode=0 / cycle_ok=true
failed_cycles=0
loop_ok=true
same_m15_no_signal_skipped=true
router=SKIPPED_SAME_M15_NO_SIGNAL
router_seconds=0.0
total_seconds=約1.3秒
```

安全確認:

```text
send_flag_passed_by_this_runner=false
sender_order_send_called_count=0
sender_sent_rows=0
production_registry_mutated_by_this_runner=false
```

---

## guarded demo send 設計

設計書:

```text
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN.md
```

方針:

```text
通常 dry-run wrapper は永久に no-send
send可能入口は専用 guarded demo send wrapper / BAT に分離
--allow-demo-send と --send の二重承認が揃った時だけ sender に --send を渡せる
production registry write はまだ実装しない
```

---

## 新規追加済み guarded demo send once wrapper

追加ファイル:

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py
```

コミット:

```text
e5bb8fad38fcc608c410758855c51db30434ae7a
```

目的:

```text
1. 既存 sidecar dry-run flow を実行
2. 生成された order_payloads.csv を確認
3. guarded sender stage を別段で実行可能にする
4. ただし sender に --send を渡すには二重承認が必要
```

---

## guarded demo send once の二重承認仕様

```text
--send なし / --allow-demo-send なし:
  sender に --send を渡さない
  send_suppressed_reason=SEND_NOT_REQUESTED

--send あり / --allow-demo-send なし:
  sender に --send を渡さない
  send_suppressed_reason=ALLOW_DEMO_SEND_NOT_SET

--send なし / --allow-demo-send あり:
  sender に --send を渡さない
  send_suppressed_reason=SEND_NOT_REQUESTED

--send あり / --allow-demo-send あり:
  payload rows > 0 かつ guard 条件OKの時だけ sender に --send を渡せる
```

初期guard:

```text
expected-login=75539039
require-demo-account=true
broker-symbol=GOLD#
fixed-lot=0.01
max-orders=1
position-policy=block_any
max-symbol-positions=1
max-symbol-lot=0.01
```

---

## guarded demo send once 実行確認 1: no flags

実行:

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py
```

結果:

```text
cycle_ok=true
allow_demo_send=false
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
payload_rows_out=0
guarded_sender=SKIPPED_NO_PAYLOAD_ROWS
guarded_sender_order_send_called_count=0
guarded_sender_sent_rows=0
production_registry_mutated=false
```

この実行では、dry_run_stage は通常scan。`same_m15_skip_reason=NO_PREVIOUS_RUNTIME_STATE` だったため router は通常実行。

```text
router_seconds=4.483
total_seconds=6.457
```

これは fresh out-dir で runtime_state がまだ無かったため正常。

---

## guarded demo send once 実行確認 2: --send only

実行:

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py --send
```

結果:

```text
cycle_ok=true
allow_demo_send=false
send_requested=true
send_flag_passed_to_sender=false
send_suppressed_reason=ALLOW_DEMO_SEND_NOT_SET
payload_rows_out=0
guarded_sender=SKIPPED_NO_PAYLOAD_ROWS
guarded_sender_order_send_called_count=0
guarded_sender_sent_rows=0
production_registry_mutated=false
```

この実行では、同じM15 no-signal skip が発動。

```text
same_m15_no_signal_skipped=true
router=SKIPPED_SAME_M15_NO_SIGNAL
router_seconds=0.0
dry_run_stage_seconds=1.969
total_seconds=1.984
```

重要:

```text
--send を付けても --allow-demo-send が無いので sender に --send は渡っていない
order_send_called_count=0
sent_rows=0
```

---

## 現在の重要な安全確認

```text
--send 単独では実送信されない
normal dry-run wrapper は --send を渡さない
guarded sender も payload rows 0 なら起動しない
production registry write はない
既存 Mochipoyo BAT は変更していない
既存 Mochipoyo ledgers は変更していない
既存 trigger-state files は変更していない
```

---

## まだ実行していないこと

以下は未実施。

```text
python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py --allow-demo-send
python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py --allow-demo-send --send
```

特に以下は、まだ実行しないこと。

```text
--allow-demo-send --send
```

理由:

```text
現状 no-signal で payload rows 0 なので実送信はされない見込みだが、次はまず suppression validation を自動化してから進む
```

---

## 次にやるべきこと

### 1. guarded demo send safety validation を作る

候補ファイル:

```text
scripts/run_gold_multi_strategy_guarded_demo_send_safety_validation.py
scripts/run_gold_multi_strategy_guarded_demo_send_safety_validation.bat
```

検証ケース:

```text
Case 1: no flags
  expected: send_flag_passed_to_sender=false, reason=SEND_NOT_REQUESTED

Case 2: --send only
  expected: send_flag_passed_to_sender=false, reason=ALLOW_DEMO_SEND_NOT_SET

Case 3: --allow-demo-send only
  expected: send_flag_passed_to_sender=false, reason=SEND_NOT_REQUESTED

Case 4: payload rows 0 + --allow-demo-send --send
  expected: send_flag_passed_to_sender=false, reason=NO_PAYLOAD_ROWS
```

注意:

```text
Case 4 は payload rows 0 の時だけ安全。
現状 no-signal なので payload rows 0。
ただし signal が出ている局面では Case 4 は sender に --send が渡る可能性がある。
そのため validation では --allow-demo-send --send を実CSV live payloadで使わず、payload rows 0 を事前確認するか、mock/no-payload fixtureで検証すること。
```

### 2. 標準確認に guarded safety validation を追加する

対象:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

追加するのは、実MT5 order_send を伴わない suppression validation のみ。

### 3. まだ production registry write は実装しない

sender native registry preview は既にあるが、production write は別段階。

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

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
- 標準確認 scripts\run_gold_multi_strategy_case_matrix_validation.bat は ALL PASS
- monitor skip A/B PASS
- same-M15 no-signal skip A/B PASS
- sidecar dry-run単発 PASS
- forever aligned dry-run PASS
- 毎分02秒起動 OK
- same-M15 no-signal skip により同じM15 no-signal時は router_seconds=0.0、total_seconds約1.3秒
- --send は通常dry-runでは未使用
- order_send_called_count=0
- sent_rows=0
- production registry writeなし

今回 guarded demo send once wrapper を追加済み:
- scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py

このwrapperは、sender に --send を渡す条件を二重承認にしています。
- --send だけでは送信しない
- --allow-demo-send だけでも送信しない
- --allow-demo-send と --send の両方が揃い、payload rows > 0 かつ guard OK の時だけ sender に --send を渡せる設計

実行確認済み:
1. python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py
   - cycle_ok=true
   - send_flag_passed_to_sender=false
   - send_suppressed_reason=SEND_NOT_REQUESTED
   - payload_rows_out=0
   - order_send_called_count=0
   - sent_rows=0

2. python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py --send
   - cycle_ok=true
   - send_flag_passed_to_sender=false
   - send_suppressed_reason=ALLOW_DEMO_SEND_NOT_SET
   - payload_rows_out=0
   - order_send_called_count=0
   - sent_rows=0

まだ実行していないもの:
- --allow-demo-send
- --allow-demo-send --send

次にやること:
1. guarded demo send safety validation を作る
   - no flags
   - --send only
   - --allow-demo-send only
   - payload rows 0 fixtureで --allow-demo-send --send suppression
2. その validation を標準確認BATへ追加
3. まだ production registry write は実装しない
4. まだ実CSV signal で --allow-demo-send --send は実行しない

重要:
既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC統合はまだ触らないでください。
```

---

## 現時点の結論

```text
軽量化済み sidecar dry-run は実用速度でPASS。
guarded demo send once wrapper は追加済み。
--send単独の送信抑止は確認済み。
次は guarded demo send safety validation を自動化する段階。
本当の demo order_send はまだ行わない。
```
