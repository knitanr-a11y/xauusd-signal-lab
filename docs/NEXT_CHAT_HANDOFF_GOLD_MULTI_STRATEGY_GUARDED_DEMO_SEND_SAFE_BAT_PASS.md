# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS

## 目的

GOLD BUY/SELL multi-strategy sidecar guarded demo send flow で、安全な BAT 入口の no-send / allow-only が PASS した状態を次チャットへ引き継ぐ。

現在も、既存 Mochipoyo 本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として構築中。

今回の到達点は、guarded demo send once wrapper の安全BAT入口を2本追加し、以下がすべて PASS した段階。

```text
1. 標準確認BAT
2. guarded demo-send once no-send BAT
3. guarded demo-send once allow-only BAT
```

まだ `--allow-demo-send --send` を含む armed / 実送信BAT は作っていない。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFE_BAT_PASS.md
```

併読推奨:

```text
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

## 今回追加済みの設計doc

```text
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
```

この設計では、BAT入口を以下のように分ける。

```text
通常 dry-run BAT:
  永久に no-send

Guarded demo send no-send BAT:
  --allow-demo-send なし
  --send なし

Guarded demo send allow-only BAT:
  --allow-demo-send あり
  --send なし

Guarded demo send armed BAT:
  --allow-demo-send --send あり
  今回はまだ作らない
```

重要:

```text
--allow-demo-send --send を含む実送信BATはまだ作らない。
MT5 demo order_send はまだしない。
production registry write もまだ実装しない。
```

---

## 今回追加済みの安全BAT

### 1. no-send BAT

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_no_send.bat
```

特徴:

```text
--allow-demo-send なし
--send なし
```

期待値:

```text
allow_demo_send=false
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
order_send_called_count=0
sent_rows=0
production_registry_mutated=false
```

出力先:

```text
data/r/gds_once_no_send
```

### 2. allow-only BAT

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_only.bat
```

特徴:

```text
--allow-demo-send あり
--send なし
```

期待値:

```text
allow_demo_send=true
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
order_send_called_count=0
sent_rows=0
production_registry_mutated=false
```

出力先:

```text
data/r/gds_once_allow_only
```

---

## 実行済み確認 1: 標準確認BAT

実行:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

結果:

```text
GOLD guarded demo-send safety validation exit code: 0
GOLD standard validation ALL PASS
```

summary:

```text
Case Matrix summary: data\research_results\gold_multi_strategy_case_matrix_validation\latest_gold_multi_strategy_case_matrix_validation_result.json
Monitor skip A/B summary: data\r\msab\latest_gold_multi_strategy_monitor_skip_ab_validation_result.json
Same-M15 skip A/B summary: data\r\sm15ab\latest_gold_multi_strategy_same_m15_skip_ab_validation_result.json
Guarded demo-send safety summary: data\r\gdsafe\latest_gold_multi_strategy_guarded_demo_send_safety_validation_result.json
```

安全確認:

```text
guarded demo-send safety validation: PASS
validation_ok=true
checks_failed=0
send_flag_passed_to_sender_any_case=false
order_send_called_count_total=0
sent_rows_total=0
production_registry_mutated=false
live_csv_wrapper_ran_with_allow_demo_send_and_send=false
```

---

## 実行済み確認 2: no-send BAT

実行:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_no_send.bat
```

結果:

```text
GOLD guarded demo-send once NO-SEND exit code: 0
summary_json: data\r\gds_once_no_send\latest_gold_multi_strategy_guarded_demo_send_once_result.json
```

確認値:

```text
cycle_ok=true
allow_demo_send=false
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
payload_rows_out=0
guarded_sender_order_send_called_count=0
guarded_sender_sent_rows=0
production_registry_mutated=false
```

---

## 実行済み確認 3: allow-only BAT

実行:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_only.bat
```

結果:

```text
GOLD guarded demo-send once ALLOW-ONLY exit code: 0
summary_json: data\r\gds_once_allow_only\latest_gold_multi_strategy_guarded_demo_send_once_result.json
```

確認値:

```text
cycle_ok=true
allow_demo_send=true
send_requested=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
payload_rows_out=0
guarded_sender_order_send_called_count=0
guarded_sender_sent_rows=0
production_registry_mutated=false
```

---

## 実行ログから確認できた最新CSV状態

今回の実行時点では no-signal。

```text
latest_confirmed_m15_close_time_fast=2026-05-08 23:45:00
BUY signal_found=false
SELL signal_found=false
signals_found_count=0
open_order_intent_count=0
close_intent_count=0
payload_rows_out=0
valid_order_payloads=0
```

payload rows 0 のため、guarded sender は skip。

```text
guarded sender skipped because payload rows are 0
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
--send 単独の抑止: PASS
--allow-demo-send 単独の抑止: PASS
payload rows 0 fixtureでの --allow-demo-send --send 抑止: PASS
send_flag_passed_to_sender=false
order_send_called_count=0
sent_rows=0
production registry writeなし
```

---

## まだ作っていないもの

以下はまだ存在しない/作っていない。

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_armed.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_demo_send_and_send.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_send.bat
```

理由:

```text
--allow-demo-send --send が揃うと、payload_rows_out > 0 かつ guard OK の場合に sender へ --send が渡り得る。
実CSV signal 発生時の 1件 demo send は、さらに別段階でユーザー明示承認後に行う。
```

---

## まだ実施していないこと

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
1. safe BAT PASS を docs に固定する  ※このファイルで完了
2. sidecar forever aligned dry-run を継続し、実CSV signal が出るかを見る
3. 実CSV signal が出た状態かどうかを guarded wrapper no-send / allow-only で確認する
4. payload_rows_out=1 になった場合でも、すぐ --send はしない
5. 標準確認 BAT を再実行して ALL PASS を確認する
6. その後、ユーザー明示承認がある場合のみ armed BAT の設計/作成を検討する
7. armed BAT を作る場合も、名前・警告・停止条件・max-orders=1 / fixed-lot=0.01 / block_any を固定する
8. demo send 後も production registry write は別段階
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

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
- --send 単独では sender に --send が渡らない
- --allow-demo-send 単独でも sender に --send が渡らない
- payload rows 0 fixture で --allow-demo-send --send 相当でも sender に --send が渡らない
- send_flag_passed_to_sender=false
- order_send_called_count=0
- sent_rows=0
- production registry writeなし

今回追加済み:
- docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN.md
- scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_no_send.bat
- scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_only.bat

実行確認済み:
1. scripts\run_gold_multi_strategy_case_matrix_validation.bat
   - GOLD standard validation ALL PASS
2. scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_no_send.bat
   - cycle_ok=true
   - send_flag_passed_to_sender=false
   - send_suppressed_reason=SEND_NOT_REQUESTED
   - order_send_called_count=0
   - sent_rows=0
3. scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_only.bat
   - cycle_ok=true
   - send_flag_passed_to_sender=false
   - send_suppressed_reason=SEND_NOT_REQUESTED
   - order_send_called_count=0
   - sent_rows=0

重要:
- まだ armed / 実送信BAT は作っていない
- まだ実CSV signal で --allow-demo-send --send は実行しない
- まだ MT5 demo order_send はしない
- まだ production registry write は実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC統合はまだ触らない

次にやること:
1. sidecar forever aligned dry-run を継続し、実CSV signal が出るかを見る
2. 実CSV signal が出たら、まず no-send / allow-only で payload_rows_out=1 になるか確認する
3. すぐ --send はしない
4. 標準確認 ALL PASS を再確認する
5. その後、ユーザー明示承認がある場合のみ armed BAT の設計/作成を検討する
```

---

## 現時点の結論

```text
guarded demo send は、安全な入口BAT 2本まで PASS。
まだ実送信可能な armed BAT は存在しない。
次は signal-present 状態を dry-run / allow-only で待つ段階。
```
