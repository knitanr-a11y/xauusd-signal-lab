# GOLD_ML_V1 Batch016後 引き継ぎ追補

更新日: 2026-06-24

この追補は `NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md` の「次の作業」を更新する。従来の候補定義・評価契約・禁止事項は変更しない。

## 現在地点

積み重ね候補は引き続き6本で、候補ロジック変更・追加・削除はない。

- GML1-PROV-007
- GML1-PROV-008
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-014-A

現在もaudit-only。`live_ready=false`、`final_signal=false`、`mt5_order=false`、`discord=false`。

## 今回完了した実装

### Batch015: 6候補 overlap・独立性監査

実装済み:

- `config/gold_ml_v1/candidate_overlap_audit_20260624.json`
- `scripts/gold_ml_v1/audit/candidate_overlap_audit.py`
- `scripts/gold_ml_v1/audit/run_candidate_overlap_audit.bat`
- `tests/gold_ml_v1/test_candidate_overlap_audit.py`
- `config/gold_ml_v1/candidate_overlap_audit_batch015_status_20260624.json`
- `docs/gold_ml_v1/GOLD_ML_V1_BATCH015_OVERLAP_AUDIT_IMPLEMENTATION_20260624.md`

出力対象:

- exact entry overlap / Jaccard
- ±1 decision-bar overlap
- concurrent exposure
- parent-child retention
- monthly R correlation / effective rank
- year / quarter / session / regime concentration
- all / pre-2026 / 2026 diagnostic / fresh post-cutoffの分離
- input/output SHA256 manifest

実候補matrixは未生成。理由は6本すべてのexact trade-registry CSV本体がrepoにないため。集計値からentry timestampを推定してはならない。

### PROV-020 fresh filter activation monitor

実装済み:

- `config/gold_ml_v1/prov020_fresh_filter_activation_monitor_20260624.json`
- `scripts/gold_ml_v1/prospective/prov020_fresh_filter_activation_monitor.py`
- `scripts/gold_ml_v1/prospective/run_prov020_fresh_filter_activation_monitor.bat`
- `tests/gold_ml_v1/test_prov020_fresh_filter_activation_monitor.py`
- `config/gold_ml_v1/prov020_fresh_filter_activation_monitor_status_20260624.json`
- `docs/gold_ml_v1/GOLD_ML_V1_PROV020_FRESH_FILTER_ACTIVATION_MONITOR_20260624.md`

固定監視条件:

- PROV-015 parent event
- MT5 server closeが `2026-06-23 18:15:00` より後
- server hour 08-16 inclusive
- `H1_SPREAD_PRICE_DIV_ATR14 >= 0.0308778597897866`

monitorはdecision時点既知の3列だけを読む。exit、TP/SL、realized R、MAE/MFE、将来horizonを読まない。append-only ledgerは同一decision timeの内容変更をfail closedする。

実データ上のfresh activation有無は未確定。exact prospective PROV-015 parent-event CSV本体が必要。

### Batch016: WATCH-014-A centroid・seed安定性監査

実装済み:

- `config/gold_ml_v1/watch014_centroid_seed_stability_audit_20260624.json`
- `scripts/gold_ml_v1/audit/watch014_centroid_seed_stability_audit.py`
- `tests/gold_ml_v1/test_watch014_centroid_seed_stability_audit.py`
- `config/gold_ml_v1/watch014_centroid_seed_stability_status_20260624.json`
- `docs/gold_ml_v1/GOLD_ML_V1_WATCH014_CENTROID_SEED_STABILITY_AUDIT_20260624.md`

監査方法:

- 54 path-shape features
- StandardScaler fitは2023のみ
- centroid alignmentも2023 assignmentだけ
- Hungarian assignmentでseed間の任意cluster番号を対応付け
- centroid Euclidean/cosine
- membership Jaccard
- ARI / NMI / exact aligned fraction
- train-2023 / pre-2026 / 2026 diagnostic / freshを分離
- 2026でcluster選択や閾値変更をしない

実centroid・seed安定性結果は未生成。Batch014のexact 54-feature registryと、seed 7307/7001/7021/7041/7061/7081のexact assignment registryが必要。

## テストと依存関係

ローカル合成テストは合計7件PASS。

監査専用依存関係:

- `scripts/gold_ml_v1/requirements-audit.txt`

repo全体のruntime requirementsは変更していない。

## 次に行う順序

1. exact registryが入手できる場合、Batch015を実行し全出力を目視監査する。
2. exact prospective PROV-015 parent eventがある場合、PROV-020 fresh monitorを実行する。
3. exact Batch014 feature/assignment registryがある場合、Batch016を実行する。
4. 入力本体がまだない場合は、既知集計から結果を再構成せず、P0-4のMAE/MFE・TP到達時間・停滞時間監査パッケージをaudit-onlyで実装する。
5. その後、独立SHORT、stable regime transition、前週・前月高安とopening range acceptance/rejectionへ進む。
6. 十分に絞った候補だけshortlist-only local replay packageへ進める。
7. GOLD_ML_V1 prospective runtimeは最後。live/final_signal/MT5/Discordは明示許可までOFF。

## 絶対に結果扱いしないもの

- 合成テストのoverlap値
- exact registryなしの推定entry overlap
- exact prospective eventなしのPROV-020 activation推測
- feature/assignment本体なしのWATCH-014 centroid推測
- 2026を使った閾値・cluster・候補選択

## 正本

最新の状態は次を優先する。

1. `config/gold_ml_v1/current_state_snapshot_20260624.json`
2. この追補
3. 各Batch015/PROV020/Batch016 status JSON
4. 元の `NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md`
