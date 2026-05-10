# GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_BAT_ENTRY_DESIGN

## 目的

GOLD BUY/SELL multi-strategy sidecar flow の guarded demo send once wrapper へ進むための BAT 入口設計を固定する。

この設計では、まだ MT5 demo order_send は実行しない。

今回の対象は以下のみ。

```text
1. guarded demo send once wrapper を呼ぶ安全な BAT 入口を分ける
2. no-send / allow-only の安全BATを用意する
3. --allow-demo-send --send を含む実送信BATはまだ作らない
4. production registry write はまだ実装しない
```

---

## 前提

直近の到達点:

```text
Case Matrix: PASS
Monitor skip A/B: PASS
Same-M15 no-signal skip A/B: PASS
Guarded demo-send safety validation: PASS
Standard validation BAT: ALL PASS
sidecar dry-run単発: PASS
forever aligned dry-run: PASS
毎分02秒起動: OK
order_send_called_count=0
sent_rows=0
production registry writeなし
```

関連ファイル:

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py
scripts/run_gold_multi_strategy_guarded_demo_send_safety_validation.py
scripts/run_gold_multi_strategy_case_matrix_validation.bat
```

最新 handoff:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS.md
```

---

## 現在の guarded demo send once wrapper の送信条件

wrapper は以下の二重承認仕様。

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
  payload_rows_out > 0 かつ guard OK の時だけ sender に --send を渡せる
```

そのため、BAT 入口もこの区別が視覚的に分かる名前に分ける。

---

## BAT 入口を分ける理由

通常 dry-run BAT に `--send` 可能性を混ぜると、どこから実送信され得るか分かりにくくなる。

そのため、入口を以下のように分離する。

```text
通常 dry-run BAT:
  永久に no-send

Guarded demo send no-send BAT:
  guarded wrapper の経路確認だけ
  --allow-demo-send も --send も付けない

Guarded demo send allow-only BAT:
  allow flag のみ通すが --send は付けない
  二重承認の片側だけなので実送信されない

Guarded demo send armed BAT:
  --allow-demo-send --send を付ける実送信候補
  今回はまだ作らない
```

---

## 今回作る安全BAT

### 1. no-send BAT

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_no_send.bat
```

役割:

```text
guarded demo send once wrapper の入口確認
--allow-demo-send なし
--send なし
sender に --send は渡らない
```

期待値:

```text
send_requested=false
allow_demo_send=false
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
order_send_called_count=0
sent_rows=0
production_registry_mutated=false
```

### 2. allow-only BAT

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_only.bat
```

役割:

```text
--allow-demo-send だけを付けた状態の入口確認
--send は付けない
二重承認の片側だけなので sender に --send は渡らない
```

期待値:

```text
send_requested=false
allow_demo_send=true
send_flag_passed_to_sender=false
send_suppressed_reason=SEND_NOT_REQUESTED
order_send_called_count=0
sent_rows=0
production_registry_mutated=false
```

---

## 今回まだ作らないBAT

以下はまだ作らない。

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

## BAT の固定 guard 値

初回入口確認では保守設定を使う。

```text
broker-symbol=GOLD#
expected-login=75539039
require-demo-account=true
fixed-lot=0.01
magic=26050601
max-orders=1
deviation=50
position-policy=block_any
max-symbol-positions=1
max-symbol-lot=0.01
```

---

## 出力先

BAT ごとに出力先を分ける。

```text
no-send:
  data\r\gds_once_no_send

allow-only:
  data\r\gds_once_allow_only
```

標準 safety validation は引き続き以下。

```text
data\r\gdsafe
```

---

## 実行順

安全な確認順:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_no_send.bat
scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once_allow_only.bat
```

期待:

```text
1. Standard validation: GOLD standard validation ALL PASS
2. no-send BAT: send_flag_passed_to_sender=false / order_send_called_count=0 / sent_rows=0
3. allow-only BAT: send_flag_passed_to_sender=false / order_send_called_count=0 / sent_rows=0
```

---

## 失敗時の停止条件

以下が1つでも出たら停止。

```text
cycle_ok=false
send_flag_passed_to_sender=true
order_send_called_count > 0
sent_rows > 0
production_registry_mutated=true
expected-login mismatch
require-demo-account guard NG
```

no-send / allow-only BAT では、`send_flag_passed_to_sender=true` は即失敗扱い。

---

## この段階で確認すること

```text
BAT入口名を見ただけで送信可能性が分かる
通常 dry-run BAT には一切 --send を入れない
allow-only BAT でも --send は入れない
armed BAT はまだ存在しない
標準 validation は引き続き ALL PASS
```

---

## まだやらないこと

```text
実CSV signal あり状態での --allow-demo-send --send 実行
MT5 demo order_send
production position_registry.csv write
send成功後 registry write
close intent MT5 execution
BTC integration
既存 Mochipoyo 本体BATへの統合
```

---

## 次段階

この no-send / allow-only BAT が確認できた後、次段階で以下を検討する。

```text
1. 実CSV signal が出た状態かどうかを確認
2. 標準確認 BAT を再実行して ALL PASS を確認
3. payload_rows_out=1 のときだけ、実送信用 armed BAT を別名で作るか判断
4. armed BAT はユーザー明示承認なしでは作らない/実行しない
5. 初回 demo send は max-orders=1 / fixed-lot=0.01 / block_any のまま行う
6. demo send 後も production registry write は別段階
```

---

## 結論

今回の BAT 入口設計では、guarded demo send wrapper の経路確認を進めるが、まだ実送信可能な BAT は作らない。

安全な入口として no-send BAT と allow-only BAT だけを作り、`order_send_called_count=0` と `sent_rows=0` を維持する。
