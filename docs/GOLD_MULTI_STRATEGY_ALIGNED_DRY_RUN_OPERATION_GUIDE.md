# GOLD_MULTI_STRATEGY_ALIGNED_DRY_RUN_OPERATION_GUIDE

## 目的

GOLD BUY/SELL multi-strategy sidecar flow を、実送信なしの aligned dry-run 実運用ループとして動かすための手順を固定する。

この段階では、まだ MT5 demo order_send はしない。

---

## 対象フロー

```text
GOLD BUY/SELL multi-strategy
  -> sidecar dry-run router
  -> autotrade adapter dry-run
  -> Mochipoyo payload bridge dry-run
  -> sender dry-run / no-send
```

実運用dry-runの起動BAT:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

最新状態確認BAT:

```bat
scripts\show_gold_multi_strategy_aligned_dry_run_status.bat
```

---

## 安全境界

この運用手順では以下を守る。

```text
--send を渡さない
MT5 order_send を呼ばない
production position_registry.csv を書かない
既存 Mochipoyo 本体BATを呼ばない
既存 ledgers / trigger-state を意図的に変更しない
BTC統合に触らない
close intent MT5 execution に触らない
```

---

## 事前確認

実運用dry-runを起動する前に、標準確認BATが ALL PASS であること。

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

期待:

```text
GOLD standard validation ALL PASS
```

---

## 実運用dry-run起動

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

このBATは以下の設定で動く。

```text
max-cycles=0
interval-minutes=1
offset-seconds=2
no-run-immediately=true
```

つまり、毎分02秒に起動し、最新確定M15を評価する。

停止:

```text
Ctrl+C
```

---

## コンソール表示

現在の aligned runner は compact console output がデフォルト。

コンソールには1サイクルごとに以下だけ表示される。

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

子プロセスの長い stdout/stderr はコンソールに流れず、以下に保存される。

```text
data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned\command_logs\*.txt
```

---

## 最新状態だけ見たい場合

別コンソールまたは停止後に以下を実行する。

```bat
scripts\show_gold_multi_strategy_aligned_dry_run_status.bat
```

これは read-only。

以下だけを表示する。

```text
status_ok
loop_ok
cycles_run
failed_cycles
last_cycle_index
last_cycle_ok
last_cycle_end_utc
latest_m15
same_m15_no_signal_skipped
signals_found_count
open_order_intent_count
close_intent_count
payload_rows_out
valid_order_payloads
order_send_called_count
sent_rows
next_run_utc
stdout_log
aligned_loop_log_csv
summary_json
```

---

## signal が出ていない通常状態

期待値:

```text
cycle_ok=true
signals_found_count=0
open_order_intent_count=0
payload_rows_out=0
order_send_called_count=0
sent_rows=0
```

same-M15 no-signal skip が効く場合:

```text
same_m15_no_signal_skipped=true
router_seconds=0.0
total_seconds roughly around 1-2 seconds
```

---

## signal が出た場合

signal が出た場合、まず以下のような値になる可能性がある。

```text
signals_found_count>=1
open_order_intent_count>=1
payload_rows_out>=1
valid_order_payloads>=1
```

ただし、この段階ではまだ `--send` しない。

signal が出た場合の次手順:

```text
1. Ctrl+C で forever aligned dry-run を停止
2. 標準確認BATを再実行して ALL PASS を確認
3. no-send BAT / allow-only BAT で payload_rows_out を再確認
4. stdout_log と summary_json を保存
5. すぐ --allow-demo-send --send は実行しない
6. ユーザー明示承認がある場合のみ armed BAT の設計/作成へ進む
```

---

## 失敗時の停止条件

以下が1つでも出たら停止。

```text
cycle_ok=false
returncode != 0
order_send_called_count > 0
sent_rows > 0
production_registry_mutated=true
expected-login mismatch
require-demo-account guard NG
```

特に dry-run loop で以下が出た場合は即停止。

```text
order_send_called_count > 0
sent_rows > 0
```

dry-run では常に 0 でなければならない。

---

## デバッグ時だけ詳細ログをコンソールにも出す

通常は不要。

どうしても詳細をコンソールに流したい場合だけ、直接 Python に `--echo-wrapper-output` を付ける。

```bat
python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py --out-dir data\r\aligned_verbose_test --max-cycles 1 --echo-wrapper-output
```

実運用dry-run BAT には `--echo-wrapper-output` を付けない。

---

## まだやらないこと

```text
armed / 実送信BATの作成
実CSV signal あり状態での --allow-demo-send --send 実行
MT5 demo order_send
production position_registry.csv write
send成功後 registry write
close intent MT5 execution
BTC integration
既存 Mochipoyo 本体BATへの統合
```

---

## 結論

この段階では、GOLD multi-strategy sidecar を compact console の aligned dry-run 実運用ループとして回す。

signal-present 状態を検知しても、すぐに実送信へ進まず、まず dry-run/no-send/allow-only で payload を確認し、標準確認 ALL PASS を再確認する。
