# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_SAME_M15_SKIP

## 目的

GOLD BUY/SELL multi-strategy sidecar dry-run loop の軽量化到達点を固定する。

既存もちぽよ本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として構築中。

今回の主目的は、毎分 02 秒 loop でも 1 loop が数秒以内で終わるようにすること。

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

## 標準確認コマンド

現時点の標準確認コマンドは以下 1 本。

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

この BAT は以下を一括で検証する。

```text
1. Case Matrix 4ケース
2. monitor skip A/B invariance
3. same-M15 no-signal skip A/B invariance
```

期待値:

```text
GOLD standard validation ALL PASS
```

---

## 最新 PASS 状態

最新実行では以下すべて PASS。

```text
Case Matrix: PASS
Monitor skip A/B: PASS
Same-M15 skip A/B: PASS
```

標準確認の最後:

```text
GOLD standard validation ALL PASS
```

---

## Case Matrix 4ケース

標準確認内の Case Matrix は以下 4 ケース。

```text
Case A: no-signal dry-run path
Case B: sender-native registry/policy path
Case C: mock signal-present path
Case D: minute-aligned one-cycle path
```

期待値:

```text
case_matrix_ok=true
checks_total=4
checks_failed=0
```

---

## 軽量化 1: monitor skip

### 目的

no-signal かつ dry-run signal ledger に未解決 signal がない場合、position monitor を起動しない。

### 対象

```text
BUY dry-run cycle
SELL dry-run loop
multi-strategy router
mochipoyo-loop wrapper
```

### フラグ

```text
--skip-monitor-when-no-open-signals
```

### 発動条件

```text
strategy out-dir の signal_ledger.csv に DRY_RUN_SIGNAL_CREATED 行がない
```

### 安全性

```text
live_scan は通常通り実行
signal_found / signal_key / scan_reason / latest_m15_close_time は通常通り作る
monitor だけを後段で skip
DRY_RUN_SIGNAL_CREATED が1件でもあれば monitor は通常実行
```

### A/B 検証

標準確認内で以下を比較する。

```text
baseline: --skip-monitor-when-no-open-signals なし
optimized: --skip-monitor-when-no-open-signals あり
```

比較項目:

```text
signal_found
signal_key
scan_reason
latest_m15_close_time
candidate_count
latest_candidate_entry_time
signals_found_count
open_order_intent_count
close_intent_count
payload_rows_out
valid_order_payloads
```

最新結果:

```text
validation_ok=true
reason=MONITOR_SKIP_SIGNAL_INVARIANCE_PASS
checks_failed=[]
```

---

## 軽量化 2: same-M15 no-signal skip

### 目的

毎分 02 秒 loop は維持しつつ、M15足が変わっていない間、前回 no-signal だった同じ最新確定M15を何度も重く再scanしない。

M15確定足は15分に1回しか変わらないため、同じ latest confirmed M15 で前回 no-signal / no intent / no unresolved signal なら、BUY/SELL router scan を省略できる。

### フラグ

```text
--skip-same-m15-no-signal
```

### 発動条件

すべて成立した時だけ router scan を skip する。

```text
1. --skip-same-m15-no-signal が明示指定されている
2. runtime_state.json が存在する
3. 現在の latest confirmed M15 close_time が前回と同じ
4. 前回 cycle_ok=true
5. 前回 signals_found_count=0
6. 前回 open_order_intent_count=0
7. 前回 close_intent_count=0
8. 前回 BUY/SELL strategy_status が no-signal
9. BUY signal_ledger.csv に DRY_RUN_SIGNAL_CREATED がない
10. SELL signal_ledger.csv に DRY_RUN_SIGNAL_CREATED がない
```

### 発動時の期待値

```text
same_m15_no_signal_skipped=true
same_m15_skip_reason=SKIPPED_SAME_CONFIRMED_M15_PREVIOUS_NO_SIGNAL_NO_OPEN_SIGNALS
router=SKIPPED_SAME_M15_NO_SIGNAL
router_seconds=0.0
signals_found_count=0
open_order_intent_count=0
close_intent_count=0
payload_rows_out=0
valid_order_payloads=0
sender=SKIPPED_NO_PAYLOAD_ROWS
```

### A/B 検証

標準確認内で以下3段階を実行する。

```text
1. baseline_full_scan
   - same-M15 skipなしで通常scan

2. optimized_warmup_full_scan
   - same-M15 skipあり
   - fresh out-dir なので1回目は通常scan
   - runtime_state.json を作成

3. optimized_same_m15_skip
   - 同じ out-dir でもう一度実行
   - same-M15 no-signal skip を発動
```

比較項目:

```text
signal_found
signal_key
scan_reason
latest_m15_close_time
candidate_count
latest_candidate_entry_time
signals_found_count
open_order_intent_count
close_intent_count
payload_rows_out
valid_order_payloads
```

最新結果:

```text
validation_ok=true
reason=SAME_M15_NO_SIGNAL_SKIP_INVARIANCE_PASS
checks_failed=[]
warmup_not_skipped=true
```

速度例:

```text
baseline_total_seconds=5.646
baseline_router_seconds=4.451
optimized_skip_total_seconds=1.367
optimized_skip_router_seconds=0.0
```

---

## fast M15 parser

### 背景

最初の same-M15 skip 実装では、軽量判定用の latest confirmed M15 close_time が空になった。

```text
latest_confirmed_m15_close_time_fast=""
same_m15_skip_reason=LATEST_M15_FAST_UNAVAILABLE
```

BUY/SELL live_scan 側は正しく取得できていた。

```text
BUY latest_m15_close_time=2026-05-08 23:45:00
SELL latest_m15_close_time=2026-05-08 23:45:00
```

原因は fast pre-check 側の CSV parse が MT5 CSV 形式に対して弱かったこと。

### 対応

互換wrapperを追加。

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py
```

この wrapper は既存 `run_gold_multi_strategy_mochipoyo_loop_dry_run.py` を import し、以下関数だけを堅い実装に差し替える。

```text
read_latest_confirmed_m15_close_time_fast()
```

差し替え内容:

```text
複数候補ファイル名対応
goldsharp_m15.csv / goldsharp_M15.csv / xauusd_m15.csv など
複数エンコーディング対応
; , tab whitespace 分割対応
複数時刻形式対応
末尾行近辺だけを読む
M15 bar time + 15分 = close_time として返す
```

最新標準確認では、monitor skip A/B と same-M15 skip A/B の両方で以下が取れている。

```text
latest_confirmed_m15_close_time_fast=2026-05-08 23:45:00
```

前回の pandas warning も解消。

---

## 安全境界

今回の軽量化でも以下は維持。

```text
--send は未使用
order_send_called_count=0
sent_rows=0
production position_registry.csv は未書き込み
既存 Mochipoyo ledger は未変更
既存 trigger-state は未変更
既存本番BATは未変更
close intent MT5 execution は未実装/未実行
BTC router/send integration は未着手
```

---

## 重要な理解

### monitor skip

```text
live_scan 後段の monitor だけを skip
新規シグナル検出ロジックには触らない
```

### same-M15 no-signal skip

```text
同じ latest confirmed M15 で、前回 no-signal / no intent / no unresolved signal の時だけ router scan を skip
M15が変わったら通常scanに戻る
前回 signal あり / intent あり / unresolved signal ありなら skipしない
```

### バックテスト/抽出ロジックとの関係

今回の軽量化は、バックテストで作ったシグナル条件を簡略化していない。

```text
BUY/SELL live_scan の検出条件は維持
monitor skip は後段監視だけ
same-M15 skip は同じM15の前回no-signal再評価だけ省略
```

A/B 検証では、シグナル検知・intent・payload に関わる主要出力の一致を確認済み。

---

## 実運用 sidecar dry-run への適用方針

次に進むなら、実運用 sidecar dry-run BAT に以下を入れる。

```text
--skip-monitor-when-no-open-signals
--skip-same-m15-no-signal
```

ただし、fast M15 parser が必要なため、現段階では以下 wrapper 経由で運用するのが安全。

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py
```

対象候補:

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

推奨順:

```text
1. forever aligned BAT を fast_m15_patch.py 経由 + same-M15 skip 有効化
2. 数分〜15分程度 dry-run
3. standard validation を再実行
4. 問題なければ sidecar dry-run 標準として固定
```

---

## 次チャットで最初に読むべきファイル

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_SAME_M15_SKIP.md
```

併読候補:

```text
docs/GOLD_MULTI_STRATEGY_RUNTIME_LIGHTWEIGHT_LOOP_DESIGN.md
docs/GOLD_MULTI_STRATEGY_MOCHIPOYO_SIDECAR_INTEGRATION_DESIGN_REVIEW.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_CASE_MATRIX_AND_MINUTE_ALIGNED_DRY_RUN.md
```

---

## 次にやること

1. 実運用 sidecar dry-run BAT を fast_m15_patch.py 経由にする。
2. 実運用 sidecar dry-run BAT へ `--skip-same-m15-no-signal` を追加する。
3. 標準確認を実行する。

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

4. forever aligned dry-run を少し回す。

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

5. `same_m15_no_signal_skipped=true` と `router_seconds=0.0` が同じM15中に出ることを確認する。

---

## 現時点の結論

```text
monitor skip: 採用OK
same-M15 no-signal skip: A/B PASS、採用候補としてOK
fast M15 parser: patch wrapper でOK
標準確認: ALL PASS
実送信: まだ未実施
production registry write: まだ未実施
```
