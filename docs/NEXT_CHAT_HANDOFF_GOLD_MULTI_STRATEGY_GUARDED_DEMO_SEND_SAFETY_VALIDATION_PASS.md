# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS

## 目的

GOLD BUY/SELL multi-strategy sidecar flow の guarded demo send safety validation が PASS した状態を次チャットへ引き継ぐ。

現在も、既存 Mochipoyo 本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として構築中。

今回の到達点は、guarded demo send once wrapper の二重承認抑止を自動 validation 化し、それを標準確認 BAT に追加して、標準確認が ALL PASS した段階。

---

## 最初に読むべきファイル

次チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS.md
```

併読推奨:

```text
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

## 現在の標準確認コマンド

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

現在この BAT は以下を一括で検証する。

```text
1. Case Matrix 4 cases
2. Monitor skip A/B invariance
3. Same-M15 no-signal skip A/B invariance
4. Guarded demo-send safety validation
```

期待値:

```text
GOLD standard validation ALL PASS
```

今回、この標準確認が PASS 済み。

---

## 今回追加したファイル

### guarded demo send safety validation

```text
scripts/run_gold_multi_strategy_guarded_demo_send_safety_validation.py
```

目的:

```text
guarded demo send once wrapper の send suppression contract を自動検証する。
```

デフォルト出力先:

```text
data/r/gdsafe
```

summary:

```text
data/r/gdsafe/latest_gold_multi_strategy_guarded_demo_send_safety_validation_result.json
```

case log:

```text
data/r/gdsafe/guarded_demo_send_safety_case_log.csv
```

---

## guarded demo-send safety validation の検証ケース

```text
Case 1: no flags
  expected:
    send_flag_passed_to_sender=false
    send_suppressed_reason=SEND_NOT_REQUESTED

Case 2: --send only
  expected:
    send_flag_passed_to_sender=false
    send_suppressed_reason=ALLOW_DEMO_SEND_NOT_SET

Case 3: --allow-demo-send only
  expected:
    send_flag_passed_to_sender=false
    send_suppressed_reason=SEND_NOT_REQUESTED

Case 4: zero-payload fixture + --allow-demo-send --send 相当
  expected:
    send_flag_passed_to_sender=false
    send_suppressed_reason=NO_PAYLOAD_ROWS
```

重要:

```text
Case 4 は実CSV live wrapperを --allow-demo-send --send 付きで実行しない。
wrapper 内の decide_send_suppression() を直接呼ぶ zero-payload fixture 検証。
そのため、validation 実行中に実CSV側で signal が出ても、誤って MT5 sender へ --send が渡る構造ではない。
```

---

## 実行済み validation 結果

単体実行:

```bat
python scripts\run_gold_multi_strategy_guarded_demo_send_safety_validation.py
```

結果:

```text
validation_ok=true
reason=GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS
checks_total=4
checks_failed=0
failed_cases=[]
```

安全確認:

```text
live_csv_wrapper_ran_with_allow_demo_send_and_send=false
send_flag_passed_to_sender_any_case=false
order_send_called_count_total=0
sent_rows_total=0
production_registry_mutated=false
existing_mochipoyo_bat_modified=false
existing_mochipoyo_ledgers_mutated=false
trigger_state_mutated=false
```

---

## 標準確認 BAT への追加

更新済み:

```text
scripts/run_gold_multi_strategy_case_matrix_validation.bat
```

追加内容:

```bat
python scripts\run_gold_multi_strategy_guarded_demo_send_safety_validation.py --out-dir "%GUARDED_DEMO_SEND_SAFETY_OUT_DIR%"
```

出力先:

```text
set GUARDED_DEMO_SEND_SAFETY_OUT_DIR=data\r\gdsafe
```

BAT 内に以下の安全コメントを明記済み。

```text
Case 4 uses zero-payload fixture; live CSV is NOT run with both --allow-demo-send and --send
NO MT5 order_send / NO production registry write
```

---

## 標準確認 BAT 実行済み結果

実行:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

結果:

```text
GOLD guarded demo-send safety validation exit code: 0
GOLD standard validation ALL PASS
```

最後に以下 summary が表示された。

```text
Case Matrix summary: data\research_results\gold_multi_strategy_case_matrix_validation\latest_gold_multi_strategy_case_matrix_validation_result.json
Monitor skip A/B summary: data\r\msab\latest_gold_multi_strategy_monitor_skip_ab_validation_result.json
Same-M15 skip A/B summary: data\r\sm15ab\latest_gold_multi_strategy_same_m15_skip_ab_validation_result.json
Guarded demo-send safety summary: data\r\gdsafe\latest_gold_multi_strategy_guarded_demo_send_safety_validation_result.json
```

---

## 実行ログから確認できた現状

最新CSVでは no-signal。

```text
latest_m15_close_time=2026-05-08 23:45:00
BUY signal_found=false
SELL signal_found=false
signals_found_count=0
open_order_intent_count=0
close_intent_count=0
payload_rows_out=0
valid_order_payloads=0
```

payload rows 0 のため guarded sender は skip。

```text
guarded sender skipped because payload rows are 0
```

no flags:

```text
send_requested=false
allow_demo_send=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
order_send_called_count=0
sent_rows=0
```

--send only:

```text
send_requested=true
allow_demo_send=false
send_flag_passed_to_sender=false
send_suppressed_reason=ALLOW_DEMO_SEND_NOT_SET
order_send_called_count=0
sent_rows=0
```

--allow-demo-send only:

```text
send_requested=false
allow_demo_send=true
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
order_send_called_count=0
sent_rows=0
```

zero-payload fixture + --allow-demo-send --send 相当:

```text
send_flag_passed_to_sender=false
send_suppressed_reason=NO_PAYLOAD_ROWS
order_send_called_count=0
sent_rows=0
```

---

## コミット

今回の追加/更新コミット:

```text
c1a4b112d0551dbb7316262f6449856e96860f03
Add guarded demo send safety validation

78adad8bbc099ea8e47c94f7923ace21257be393
Include guarded demo send safety validation in standard BAT
```

この handoff doc 追加コミット:

```text
このファイル追加コミットを参照
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
--send 単独の抑止: PASS
--allow-demo-send 単独の抑止: PASS
payload rows 0 fixtureでの --allow-demo-send --send 抑止: PASS
order_send_called_count=0
sent_rows=0
production registry writeなし
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

理由:

```text
実CSV signal が出て payload rows > 0 の場合、sender へ --send が渡り得るため。
次は、まず guarded demo send BAT の設計と、実行手順/停止手順を明文化してから進む。
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
1. guarded demo send once BAT を作るかどうか設計する
2. BATを作る場合も、まずは no-send / allow-only 版から作る
3. --allow-demo-send --send 版は別名BATにし、ユーザー明示承認なしでは作らない/実行しない
4. 実CSV signal が出るまでは forever aligned dry-run で待つ
5. 実CSV signal が出た時だけ、標準確認 ALL PASS を再確認してから、1件だけ demo send を検討する
6. demo send 成功後も、production registry write はまだ別段階にする
```

---

## 次チャット用引き継ぎ文

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

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
- --send 単独では sender に --send が渡らない
- --allow-demo-send 単独でも sender に --send が渡らない
- payload rows 0 fixture で --allow-demo-send --send 相当でも sender に --send が渡らない
- order_send_called_count=0
- sent_rows=0
- production registry writeなし

今回追加済み:
- scripts/run_gold_multi_strategy_guarded_demo_send_safety_validation.py
- scripts/run_gold_multi_strategy_case_matrix_validation.bat に guarded demo-send safety validation を追加済み

validation 結果:
- validation_ok=true
- reason=GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS
- checks_total=4
- checks_failed=0
- send_flag_passed_to_sender_any_case=false
- order_send_called_count_total=0
- sent_rows_total=0
- production_registry_mutated=false
- live_csv_wrapper_ran_with_allow_demo_send_and_send=false

重要:
- Case 4 は実CSV live wrapperを --allow-demo-send --send 付きで実行していない
- zero-payload fixture で decide_send_suppression() を直接検証している
- まだ実CSV signal で --allow-demo-send --send は実行しない
- まだ MT5 demo order_send はしない
- まだ production registry write は実装しない
- 既存Mochipoyo本体BAT、既存ledgers、既存trigger-state、production position_registry.csv、close intent MT5 execution、BTC統合はまだ触らない

次にやること:
1. guarded demo send once BAT を作るかどうか設計する
2. 作る場合も、まず no-send / allow-only 版から
3. --allow-demo-send --send 版BATは別名にし、ユーザー明示承認なしでは作らない/実行しない
4. 実CSV signal が出るまでは forever aligned dry-run で待つ
5. 実CSV signal が出た時だけ、標準確認 ALL PASS を再確認してから、1件だけ demo send を検討する
```

---

## 現時点の結論

```text
guarded demo send の安全抑止は自動 validation 化され、標準確認 BAT に組み込まれた。
標準確認は ALL PASS。
次は demo send BAT の入口設計へ進めるが、実送信はまだしない。
```
