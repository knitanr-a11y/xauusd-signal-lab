# GOLD_MULTI_STRATEGY_MOCHIPOYO_SIDECAR_INTEGRATION_DESIGN_REVIEW

## 目的

GOLD BUY/SELL multi-strategy を、既存もちぽよ本体へいきなり直接混ぜず、既存本体を保護したまま接続していくための設計レビュー。

現時点では以下が PASS 済み。

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

標準確認コマンド:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

期待値:

```text
case_matrix_ok=true
reason=GOLD_MULTI_STRATEGY_CASE_MATRIX_PASS
checks_total=4
checks_failed=0
schema_version=gold_multi_strategy_case_matrix_validation_v3
exit code=0
```

---

## 結論

次の接続方式は、既存もちぽよ本体へ直接内蔵する方式ではなく、まず **sidecar 接続** とする。

### 採用方針

```text
既存もちぽよ本体: そのまま維持
GOLD multi-strategy: 独立 sidecar loop として毎分 02 秒に起動
送信: まだ dry-run / preview のみ
registry: まだ preview / mock / reconcile / policy validation のみ
production registry write: 未実施
```

理由:

1. 既存もちぽよ本体の ledger / trigger-state / BAT を壊さない。
2. GOLD multi-strategy 側の BUY/SELL 追加戦略を独立して監視できる。
3. `--send` 有効化前に、signal あり / no-signal / duplicate / same_strategy BLOCK を単体で検証し続けられる。
4. 既存本体へ直接統合するより、失敗時の切り離しが簡単。
5. 既存本体と同じ毎分 02 秒 cadence に揃えられている。

---

## 現在の構成

### 既存もちぽよ本体

既存本体は以下を保持する。

```text
既存 Mochipoyo strategies
既存 Mochipoyo ledgers
既存 trigger-state files
既存 production/demo BATs
既存 live/minimal/demo autotrade flow
```

現段階では、GOLD multi-strategy から既存本体へ直接書き込まない。

### GOLD multi-strategy sidecar

GOLD multi-strategy は以下の独立 flow として扱う。

```text
live CSV
→ BUY/SELL strategy runners
→ multi-strategy router
→ autotrade adapter dry-run
→ payload bridge
→ send_mt5_order_from_payload.py dry-run
→ sender-native registry preview
→ mock/reconcile/policy validation
```

主な BAT:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run.bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
scripts\run_gold_multi_strategy_mock_signal_path_validation.bat
```

---

## 接続フェーズ

### Phase 0: 検証基盤固定済み

到達済み。

標準確認:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

通すべきケース:

```text
Case A: no-signal 実運用相当
Case B: sender-native registry / policy
Case C: signal あり mock 相当
Case D: minute-aligned 1 回実行確認
```

### Phase 1: sidecar dry-run 並列運用

次の実運用に近い段階。

実行:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

挙動:

```text
毎分 02 秒
--send なし
production registry write なし
既存もちぽよ本体 BAT は呼ばない
既存 ledger / trigger-state は意図的に触らない
```

確認項目:

```text
failed_cycles=0
aligned_loop_log.csv が増え続ける
order_send_called_count=0
sent_rows=0
unexpected warning/error がない
```

この Phase 1 では、GOLD multi-strategy が独立して安定稼働するかだけを見る。

### Phase 2: sidecar guarded demo send 設計

まだ未実装。

この段階で初めて、demo send を検討する。

ただし、いきなり `--send` を有効化しない。以下を先に設計・実装する。

```text
1. explicit flag 必須
2. account guard 必須
3. demo account guard 必須
4. max orders / max lot / symbol cap 必須
5. registry-aware policy 必須
6. duplicate guard 必須
7. production registry write は disabled-by-default
8. send success 後のみ registry write する条件を検討
9. rollback / stop 手順を明文化
```

候補 flag:

```text
--enable-demo-send
--expected-login 75539039
--require-demo-account
--enable-registry-write
--registry-csv <demo_registry_path>
--require-send-success-for-registry-write
--position-policy block_same_strategy_and_opposite_direction
```

重要:

- `--enable-demo-send` と `--send` のどちらを最終 flag にするかは、既存 sender の仕様に合わせて慎重に決める。
- flag 名を増やす場合、誤操作を防ぐため二重 opt-in が望ましい。

### Phase 3: 既存もちぽよ本体との統合

まだ未実施。

Phase 1/2 が十分安定してから検討する。

統合方式は 2 案ある。

#### 案 A: sidecar 継続

既存もちぽよ本体と GOLD multi-strategy を別プロセス/別 BAT のまま運用する。

利点:

```text
既存本体を壊しにくい
停止・切り離しが簡単
strategy 追加・検証がしやすい
ログと責務が分かれる
```

欠点:

```text
2つのループを管理する必要がある
position / registry / risk の共通化が後回しになる
```

#### 案 B: 本体 orchestration へ取り込む

既存もちぽよ本体の loop/orchestrator から GOLD multi-strategy runner を呼ぶ。

利点:

```text
起動口が1つになる
全体状態管理を一元化できる可能性がある
```

欠点:

```text
既存本体への影響が大きい
ledger / trigger-state / registry の衝突リスクがある
不具合時の切り離しが難しくなる
```

推奨:

```text
当面は案 A: sidecar 継続
本体統合は最終段階
```

---

## 責務境界

### router の責務

```text
BUY/SELL strategy runner を呼ぶ
strategy_status を集約する
combined_order_intent_dry_run.jsonl を作る
combined_close_intent_dry_run.jsonl を作る
no-signal を正常ケースとして扱う
```

### adapter の責務

```text
router intent を Mochipoyo-compatible preview に変換する
duplicate signal preview を skip する
adapter_preview_ledger.csv で重複を抑止する
既存本番 ledger には書かない
```

### payload bridge の責務

```text
adapter_order_preview.csv を sender payload CSV へ変換する
fixed lot / broker symbol / magic を付与する
no adapter preview rows の場合は rows_out=0 で正常終了する
```

### sender の責務

```text
payload を読み込む
--send がない限り order_send しない
MT5 order_check dry-run を行う
registry preview を出す
production registry はまだ書かない
```

### registry preview / reconcile / policy の責務

```text
sender dry-run result から registry preview を作る
mock position を作る
registry と positions の一致を確認する
same_strategy / opposite_direction / cap を policy preview で評価する
```

---

## ledger / trigger-state / registry の分離

### 既存もちぽよ ledger

現段階では触らない。

```text
既存 Mochipoyo ledgers: 未変更
```

### GOLD multi-strategy dry-run ledger

GOLD multi-strategy sidecar 内でのみ使用。

例:

```text
data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run\...
data\research_results\gold_multi_strategy_mock_signal_path_validation\...
```

### trigger-state

現段階では既存 trigger-state を触らない。

```text
trigger_state_mutated=false
```

### registry

現段階は preview のみ。

```text
production position_registry.csv: 未書き込み
registry preview: 使用中
mock positions: 使用中
reconcile: 使用中
policy preview: 使用中
```

---

## 毎分 02 秒 timing 方針

既存もちぽよループに合わせて、GOLD multi-strategy sidecar も毎分 02 秒を標準とする。

```text
interval_minutes=1
offset_seconds=2
```

理由:

- MT5 側 CSV 更新の取りこぼしを減らす。
- 既存もちぽよ loop cadence と合わせる。
- strategy 自体は最新確定 M15 を見るため、毎分起動しても時間軸は変わらない。
- duplicate guard / ledger / router 側で同一 signal の重複を抑止する。

注意:

- Case D は 1 回実行確認。
- forever dry-run は `run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat`。

---

## `--send` 有効化前の必須ゲート

`--send` を検討する前に、最低限以下を満たすこと。

```text
1. case_matrix_validation.bat が checks_total=4 / checks_failed=0
2. forever dry-run を一定時間回して failed_cycles=0
3. signalありmock path が毎回 PASS
4. registry preview rows が期待通り作られる
5. same_strategy BLOCK が効く
6. duplicate skip が効く
7. order_send_called_count=0 / sent_rows=0 の dry-run 安全確認が維持される
8. demo account guard が明確
9. max lot / max orders / max positions が明確
10. registry write の扱いが決まっている
```

さらに、demo send を開始する場合も、初回は以下のようにする。

```text
1 strategy only
min lot only
max_orders=1
manual terminal monitoring
Discord or console notification enabled
short observation window
immediate stop command documented
```

---

## 禁止事項 / まだ触らないもの

現段階では以下を触らない。

```text
production position_registry.csv
既存 Mochipoyo production/demo BAT
既存 Mochipoyo ledgers
既存 trigger-state files
close intent MT5 execution
BTC router/send integration
```

また、以下は禁止。

```text
--send を標準 BAT に入れる
production registry write をデフォルト有効にする
既存本体 BAT の中へ無断で multi-strategy を直書きする
no-signal を異常扱いに戻す
Windows long path 非対応の深い出力処理を追加する
```

---

## 推奨される次アクション

### 次アクション 1: sidecar dry-run forever を少し長めに確認

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

確認:

```text
failed_cycles=0
aligned_loop_log.csv が増える
order_send_called_count=0
sent_rows=0
no warnings/errors
```

### 次アクション 2: BUY mock signal path を追加

現状 Case C は SELL mock signal path。

BUY 側の signal-present path も標準確認に入れると、BUY/SELL 双方で以下が確認できる。

```text
adapter
payload bridge
sender dry-run
registry preview
mock position
reconcile
same_strategy BLOCK
duplicate skip
```

### 次アクション 3: demo send 設計書の作成

まだ実装しない。

先に以下を文書化する。

```text
send enable flag
demo account guard
risk cap
registry write timing
failure handling
rollback/stop procedure
```

---

## 次チャットへの引き継ぎ

次チャットで最初に読むファイル:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_CASE_MATRIX_AND_MINUTE_ALIGNED_DRY_RUN.md
docs/GOLD_MULTI_STRATEGY_MOCHIPOYO_SIDECAR_INTEGRATION_DESIGN_REVIEW.md
```

次に実行する標準確認:

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

その後に進むなら、まず sidecar 方式のまま、BUY mock signal path 追加か、forever dry-run の長め確認へ進む。

---

## 最終判断

現段階では、既存もちぽよ本体へ直接統合しない。

次の推奨ルート:

```text
Case Matrix 4ケース維持
→ sidecar dry-run forever の安定確認
→ BUY mock signal path 追加
→ demo send 設計書
→ disabled-by-default guarded demo send 実装検討
→ 十分に検証後、本体統合の是非を再判断
```
