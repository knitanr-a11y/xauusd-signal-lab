# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_FOREVER_ALIGNED_PASS

## 目的

GOLD BUY/SELL multi-strategy sidecar dry-run loop の軽量化適用後、minute-aligned forever dry-run が正常に回ったことを固定する。

既存もちぽよ本体へ直接混ぜず、独立 sidecar dry-run / guarded demo send flow として継続中。

---

## 現在の標準確認コマンド

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

この標準確認は以下3段階を一括で実行する。

```text
1. Case Matrix 4ケース
2. monitor skip A/B invariance
3. same-M15 no-signal skip A/B invariance
```

最新期待値:

```text
GOLD standard validation ALL PASS
```

---

## 今回の到達点

以下が PASS 済み。

```text
標準確認: ALL PASS
sidecar dry-run単発: PASS
forever aligned dry-run: PASS
毎分02秒起動: OK
same-M15 no-signal skip: OK
1 loop: 約1.3秒
--send: 未使用
order_send: 0
production registry write: なし
```

---

## forever aligned dry-run 確認

実行コマンド:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

確認ログでは以下が出た。

```text
CYCLE 1: returncode=0 / cycle_ok=true / failed_cycles=0
CYCLE 2: returncode=0 / cycle_ok=true / failed_cycles=0
loop_ok=true
```

毎分02秒の起動も確認。

```text
Cycle 1: 2026-05-10 04:05:02
Cycle 2: 2026-05-10 04:06:02
next:    2026-05-10 04:07:02
```

---

## same-M15 no-signal skip の実運用 sidecar dry-run 発動確認

forever aligned dry-run 内で、同じ latest confirmed M15 の no-signal 再評価が skip された。

確認値:

```text
same_m15_no_signal_skipped=true
same_m15_skip_reason=SKIPPED_SAME_CONFIRMED_M15_PREVIOUS_NO_SIGNAL_NO_OPEN_SIGNALS
router=SKIPPED_SAME_M15_NO_SIGNAL
router_seconds=0.0
```

速度:

```text
Cycle 1 total_seconds=1.289
Cycle 2 total_seconds=1.308
```

---

## 安全確認

forever aligned dry-run 中も以下を維持。

```text
signals_found_count=0
open_order_intent_count=0
payload_rows_out=0
sender_order_send_called_count=0
sender_sent_rows=0
send_flag_passed_by_this_runner=false
production_registry_mutated_by_this_runner=false
```

つまり、実行は sidecar dry-run の範囲に留まっている。

---

## 現在の実運用 sidecar dry-run BAT

対象:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run.bat
```

現在は以下を使用する。

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py
```

有効フラグ:

```text
--skip-monitor-when-no-open-signals
--skip-same-m15-no-signal
```

安全上の意味:

```text
monitor skip:
  live_scan 後段の position monitor だけを、未解決 signal なしの場合に skip

same-M15 no-signal skip:
  前回同じ latest confirmed M15 が no-signal / no-intent / no-unresolved だった場合だけ router scan を skip
```

---

## 重要な注意

same-M15 no-signal skip は、以下の場合には発動しない。

```text
latest confirmed M15 が変わった
前回 signal_found=true
前回 open_order_intent_count > 0
前回 close_intent_count > 0
BUY/SELL signal_ledger.csv に DRY_RUN_SIGNAL_CREATED がある
runtime_state.json がない
前回 cycle_ok=false
```

そのため、M15足が変わった時には通常 scan に戻る。

---

## まだ触っていないもの

現段階で以下は未変更・未実施。

```text
--send 有効化
production position_registry.csv 書き込み
send_mt5_order_from_payload.py の production registry write 実装
既存 Mochipoyo 本体 BAT への直接統合
既存 Mochipoyo ledgers の変更
既存 trigger-state files の変更
close intent MT5 execution
BTC router/send integration
```

---

## 次の自然な段階

次は guarded demo send 設計へ戻る。

ただし、まだいきなり `--send` を入れない。

先に設計・確認するべき項目:

```text
1. demo send を有効化するための明示フラグ
2. expected-login guard
3. require-demo-account guard
4. max orders / max lot / max symbol positions
5. registry preview と production registry write の責務分離
6. send成功後だけ registry write するかどうか
7. duplicate guard / same_strategy block / opposite direction policy
8. emergency stop / rollback 手順
9. 初回は signal-present mock ではなく、実CSV signal が出た時にどう扱うか
```

推奨は、まず設計ドキュメントを作ること。

候補名:

```text
docs/GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN.md
```

---

## 次チャットで最初に読むべきファイル

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_FOREVER_ALIGNED_PASS.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_LIGHTWEIGHT_SAME_M15_SKIP.md
```

併読候補:

```text
docs/GOLD_MULTI_STRATEGY_RUNTIME_LIGHTWEIGHT_LOOP_DESIGN.md
docs/GOLD_MULTI_STRATEGY_MOCHIPOYO_SIDECAR_INTEGRATION_DESIGN_REVIEW.md
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
```

---

## 現時点の結論

```text
軽量化適用済み sidecar dry-run は実用速度に近づいた。
標準確認・単発dry-run・forever aligned dry-run はすべてPASS。
次は guarded demo send の設計に戻れる状態。
ただし、本番送信・production registry write はまだ禁止。
```
