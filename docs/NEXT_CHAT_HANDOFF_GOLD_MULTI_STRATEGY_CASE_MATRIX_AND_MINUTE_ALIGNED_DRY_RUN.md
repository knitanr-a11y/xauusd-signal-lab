# NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_CASE_MATRIX_AND_MINUTE_ALIGNED_DRY_RUN

## 目的

GOLD の BUY/SELL multi-strategy を、既存もちぽよ本体へ直接混ぜず、独立した demo dry-run / guarded demo send flow として段階検証している。

本ドキュメントは、2026-05-10 時点で到達した以下の状態を次チャットへ正確に引き継ぐためのもの。

- no-signal 実運用相当 dry-run
- sender-native registry preview / policy BLOCK
- signal あり mock intent 相当 dry-run
- 毎分 02 秒 minute-aligned runner
- Windows long path 対応
- `datetime.utcnow()` 警告除去

重要: まだ production send / production registry write へは進んでいない。

---

## 現在の戦略スロット

### BUY

- slot: `BUY_C_ENV_RR2_72H`
- strategy / condition:
  - `GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H`

目的:

- H4 C_ENV + H1 regular bullish divergence + M15 breakout 系の BUY 戦略。
- H4 で見たダイバージェンス後の上昇を取る方向の候補。

### SELL

- slot: `SELL_H1H4_BEAR_AB`
- strategy / condition:
  - `GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H`

目的:

- H1/H4 bearish context + M15 low break 系の SELL 戦略。
- H1 で示した下落を取る方向の候補。

---

## 現在の標準確認コマンド

現時点の最重要・標準確認コマンドは以下 1 本。

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

この BAT で以下 4 ケースを一括検証する。

1. Case A: no-signal 実運用相当
2. Case B: sender-native registry / policy
3. Case C: signal あり mock 相当
4. Case D: minute-aligned 1 回実行確認

期待値:

```text
case_matrix_ok=true
reason=GOLD_MULTI_STRATEGY_CASE_MATRIX_PASS
checks_total=4
checks_failed=0
schema_version=gold_multi_strategy_case_matrix_validation_v3
exit code=0
```

最新確認ではこの期待値で PASS 済み。

---

## Case Matrix の内容

### Case A: no-signal 実運用相当

呼び出し:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run.bat
```

検証内容:

```text
live CSV
→ BUY/SELL router
→ adapter
→ payload bridge
→ sender dry-run skip when no payload rows
```

最新確認結果:

```text
case_ok=true
reason=LOOP_DRY_RUN_PASS
```

no-signal 時の期待動作:

```text
BUY: NO_SIGNAL_ON_LATEST_CONFIRMED_M15
SELL: NO_SIGNAL_ON_LATEST_CONFIRMED_M15
router: OK
adapter: OK
payload bridge: OK, rows_out=0
sender: SKIPPED_NO_PAYLOAD_ROWS
order_send_called_count=0
sent_rows=0
```

### Case B: sender-native registry / policy

呼び出し:

```bat
scripts\run_gold_multi_strategy_sender_native_registry_preview_hook_validation.bat
```

検証内容:

```text
fresh MT5 tick payload
→ real send_mt5_order_from_payload.py dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender-native registry preview
→ mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
```

最新確認結果:

```text
case_ok=true
reason=SENDER_NATIVE_REGISTRY_POLICY_PASS
```

期待値:

```text
registry_preview_rows >= 1
matched_active_registry_rows >= 1
same_strategy_blocked_rows >= 1
blocked_rows >= 1
allow_rows == 0
registry_inconsistency_blocked_rows == 0
order_send_called_count == 0
sent_rows == 0
```

### Case C: signal あり mock 相当

呼び出し:

```bat
scripts\run_gold_multi_strategy_mock_signal_path_validation.bat
```

検証内容:

```text
mock router OPEN_POSITION intent
→ adapter dry-run first pass
→ payload bridge
→ sender dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender-native registry preview
→ mock position
→ reconcile
→ registry-aware same_strategy BLOCK
→ adapter duplicate pass
→ duplicate_previews_skipped=1
```

最新確認結果:

```text
case_ok=true
reason=MOCK_SIGNAL_PATH_PASS
```

期待値:

```text
adapter_first_created_one=true
payload_rows_out_one=true
sender_no_send=true
sender_dry_run_check_ok=true
registry_preview_rows=true
mock_positions_rows=true
reconcile_ok=true
policy_same_strategy_block=true
adapter_duplicate_skipped_one=true
all_returncodes_zero=true
```

安全期待値:

```text
send_flag_passed=false
sender_order_send_called_count=0
sender_sent_rows=0
production_registry_mutated=false
existing_mochipoyo_bat_modified=false
trigger_state_mutated=false
```

### Case D: minute-aligned 1 回実行確認

呼び出し:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.bat
```

検証内容:

```text
独立 dry-run wrapper を 1 回だけ実行
interval_minutes=1
offset_seconds=2
```

最新確認結果:

```text
case_ok=true
reason=MINUTE_ALIGNED_DRY_RUN_PASS
```

期待値:

```text
loop_ok=true
cycles_run>=1
failed_cycles=0
interval_minutes=1
offset_seconds=2
last_cycle.cycle_ok=true
last_cycle.sender_order_send_called_count=0
last_cycle.sender_sent_rows=0
```

---

## 継続 dry-run 用 BAT

短時間の継続 dry-run 確認用に以下を追加済み。

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

挙動:

```text
--max-cycles 0
--interval-minutes 1
--offset-seconds 2
--no-run-immediately
```

つまり、もちぽよ式ループと同じ思想で、毎分 02 秒に独立 dry-run wrapper を回す。

停止方法:

```text
Ctrl + C
```

確認済み:

```text
複数サイクル実行
failed_cycles=0
loop_ok=true
order_send_called_count=0
sent_rows=0
```

注意:

- これは dry-run forever runner。
- `--send` は渡さない。
- 既存もちぽよ本体 BAT は呼ばない。
- production registry は書かない。

---

## 安全境界

現時点で維持している安全境界:

```text
--send は渡していない
order_send_called_count=0
sent_rows=0
production position_registry.csv は未書き込み
既存 Mochipoyo ledger は未変更
既存 trigger-state は未変更
既存本番 BAT は未変更
close intent MT5 execution は未実装/未実行
BTC router/send integration は未着手
```

重要:

- `send_mt5_order_from_payload.py` は、disabled-by-default registry preview hook には対応済みだが、production registry write 用として本番化したわけではない。
- production registry write はまだ明示的に進めていない。
- 今の registry は preview / mock / reconcile / policy validation 用。

---

## Windows long path 方針

以降、このリポジトリで追加・修正する Python 出力処理は Windows long path を前提にする。

理由:

- ローカル repo が以下のような深い階層にある。

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\...
\MQL5\Files\xauusd-signal-lab\...
```

- `data\research_results\...\command_logs\...` まで伸びると Windows の通常パス制限に引っかかる可能性がある。

方針:

```text
path.write_text() を安易に使わない
Path.mkdir() を安易に直接使わない
pandas.DataFrame.to_csv() も必要なら \\?\ パス経由にする
新規 wrapper / verifier / CSV / JSON / TXT 出力は long path helper を入れる
```

既に反映済みの代表:

- `scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py`
- `scripts/run_gold_multi_strategy_case_matrix_validation.py`
- `scripts/run_gold_multi_strategy_mock_signal_path_validation.py`
- `scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py`
- `scripts/run_gold_c_env_rr2_72h_live_scan_once.py`

---

## 警告除去

`run_gold_c_env_rr2_72h_live_scan_once.py` の以下警告は修正済み。

```text
DeprecationWarning: datetime.datetime.utcnow() is deprecated
```

修正内容:

```text
datetime.utcnow() → datetime.now(UTC)
```

最新 Case Matrix 4 ケース実行では、この警告が出ていないことを確認済み。

---

## 主な追加・更新ファイル

### Case Matrix / mock / aligned

```text
scripts/run_gold_multi_strategy_case_matrix_validation.py
scripts/run_gold_multi_strategy_case_matrix_validation.bat
scripts/run_gold_multi_strategy_mock_signal_path_validation.py
scripts/run_gold_multi_strategy_mock_signal_path_validation.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.bat
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

### BUY long path / UTC 修正

```text
scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
```

---

## 最新 PASS の要約

最新標準確認:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

最新 PASS:

```text
case_matrix_ok=true
reason=GOLD_MULTI_STRATEGY_CASE_MATRIX_PASS
checks_total=4
checks_failed=0
schema_version=gold_multi_strategy_case_matrix_validation_v3
exit code=0
```

4ケース:

```text
Case A: LOOP_DRY_RUN_PASS
Case B: SENDER_NATIVE_REGISTRY_POLICY_PASS
Case C: MOCK_SIGNAL_PATH_PASS
Case D: MINUTE_ALIGNED_DRY_RUN_PASS
```

安全:

```text
send_flag_passed_by_this_validator=false
production_registry_mutated_by_this_validator=false
existing_mochipoyo_bat_modified_by_this_validator=false
```

---

## 次に進む候補

### 候補 1: 既存もちぽよ loop への統合設計レビュー

いきなり既存本体 BAT を変更せず、まず以下を設計する。

- 既存もちぽよ live/minimal/demo loop のどこに GOLD multi-strategy wrapper を差し込むか
- 本体へ直接混ぜるのか、sidecar wrapper として並列実行するのか
- trigger-state / ledger / registry の責務分離
- `--send` を有効化する前の追加 gate

推奨: まず設計書にする。

### 候補 2: production registry write の disabled-by-default 実装レビュー

現状は registry preview まで。

次に進める場合も、以下のような disabled-by-default flag 設計にする。

```text
--enable-registry-write
--registry-csv <production_or_demo_path>
--registry-write-mode append_only
--require-send-success-for-registry-write
```

まだすぐ実装しない方が安全。

### 候補 3: dry-run forever を少し長めに回す

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

を 10〜30 分程度回し、以下を確認する。

```text
failed_cycles=0
aligned_loop_log.csv が増える
order_send_called_count=0
sent_rows=0
no unexpected warnings/errors
```

### 候補 4: BUY/SELL 両方の signal あり mock を作る

現状 Case C は SELL mock signal path。

次に BUY mock signal path も追加すると、BUY_C_ENV_RR2_72H 側の adapter/payload/sender/registry/policy も signal-present 経路として標準確認に入れられる。

---

## 次チャット開始時に読むべきファイル

まずこのファイル:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_CASE_MATRIX_AND_MINUTE_ALIGNED_DRY_RUN.md
```

必要に応じて併読:

```text
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
docs/GOLD_MULTI_STRATEGY_FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_ROADMAP.md
```

存在しない場合やファイル名が変わっている場合は、`docs` 配下で `GOLD_MULTI_STRATEGY` を検索する。

---

## 重要な結論

現時点では、以下までは確認済み。

```text
no-signal 実運用相当 dry-run: PASS
signal あり mock 相当: PASS
sender-native registry preview: PASS
same_strategy BLOCK: PASS
duplicate skip: PASS
毎分 02 秒 runner: PASS
Windows long path 対応: 主要追加部分は対応済み
datetime.utcnow warning: 解消済み
```

まだ確認・実施していないこと:

```text
production send
production registry write
既存もちぽよ本体 BAT への直接統合
close intent の MT5 実行
BTC 統合
```

次に進む場合は、まず「既存もちぽよ本体へどう接続するか」の設計レビューから入るのが安全。
