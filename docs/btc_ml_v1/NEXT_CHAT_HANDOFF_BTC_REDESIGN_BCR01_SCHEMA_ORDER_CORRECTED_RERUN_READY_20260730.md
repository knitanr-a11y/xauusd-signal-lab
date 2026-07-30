# BTC候補研究 次チャット完全引き継ぎ

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T11:35:00+09:00`
- status: `BTC_REDESIGN_BCR01_V100_INVALID_SCHEMA_ORDER_CORRECTED_V101_RERUN_READY`
- authority: `LATEST_DATED_HANDOFF`

## 0. 固定入口

新チャットは必ずrepo直下の次を最初に読む。

`START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`

この文書が唯一の最新版handoffとして指定されていることを確認する。

## 1. branch hard gate

すべての読取り・更新は次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。取得不能または文書矛盾時は停止する。

## 2. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR01_SCHEMA_ORDER_CORRECTED_RERUN_READY_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR01_SCHEMA_PHYSICAL_ORDER_CORRECTION_20260730.md`
7. `configs/btc_ml_v1/bcr01_schema_physical_order_incident_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT_CONTRACT_20260730.md`
9. `configs/btc_ml_v1/btc_bcr01_outcome_blind_source_snapshot_contract_20260730.json`
10. `docs/btc_ml_v1/BTC_D1_M7C_PRIMARY_EVIDENCE_PACKAGE_AUDIT_20260730.md`
11. `docs/btc_ml_v1/BTC_D1B_COLLECTOR_LOG_AND_CODE_AUDIT_20260730.md`
12. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
13. `configs/btc_ml_v1/btc_candidate_research_redesign_contract_20260730.json`
14. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

この順番より前にrepo全体検索、古いhandoff探索、GOLD/MOCHIPOYO横断探索をしない。

## 3. startup denylist

このBTC研究の入口として次を読まない・使わない。

- `AGENTS.md` — 現在GOLD_ML_V1用
- `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
- `docs/gold_v3/**`
- `docs/gold_ml_v1/**`
- `config/gold_v3/**`
- `config/gold_ml_v1/**`
- `scripts/gold_v3/**`
- `scripts/gold_ml_v1/**`
- GOLD V2、旧GOLD、DISC8、Stage41
- 旧BTC stacking / YouTube候補handoff
- FF05 recovery V3〜V11
- 固定入口から参照されない旧state、next action、handoff

MOCHIPOYO branchの一般探索は禁止。D1でexact pathとして許可されたM7C/Collector契約ファイルとユーザー提出物だけを読み取り専用で扱う。

## 4. ユーザーの最終目的

BTCUSDで将来使える可能性のあるトレード候補システムを、二本柱で作る。

### Track A — もちぽよ由来

M7CとCollectorの実source alertを一次証拠にし、発火構造を逆推定する。完全複製を最終目的にせず、BTCでの収益性・安定性・損失制御を優先する。ただしsource fidelityとvalue improvementを混同しない。

### Track B — 独立ベクトル

もちぽよのRCI/EMA/state transitionの微調整ではなく、異なる相場原理から候補を作る。最終的に発火重複、損益相関、共同DD、regime補完性を評価する。

## 5. D1到達点

M7C一次証拠とCollector provenance監査は完了している。

- M7C supported source events: 90
- supported BTCUSD: 51
- Collector combined cycles: 12,612
- successful cycles: 12,606
- transient failures: 6
- inserted raw rows: 127
- duplicate rows: 0
- latest observed cursor in D1B: 189
- outcome performance interpretation: not performed

## 6. BCR01目的

active SQLite DBをread-only/query-onlyで開き、consistent read transactionから次の4tableだけを論理exportする。

- `collector_state`
- `raw_alerts`
- `raw_alert_annotations`
- `collection_runs`

次はquery・exportしない。

- `episodes`
- `episode_events`
- `episode_build_anomalies`
- `episode_build_runs`
- `mt5_alignment`
- `feature_snapshots`
- `virtual_entries`
- `outcomes`

raw SQLite DB、WAL、SHMはcopy・uploadしない。

## 7. 初回BCR01提出と事故

初回提出:

`99_UPLOAD_PACKAGE(101).zip`

SHA256:

`47c38b81a465f1fa9adfbcd7901644cca8d3ab4f03f71cb9dd7353b368b602f1`

ZIPはerror用2ファイルのみで、snapshotは作成されていない。

- `outcomes_opened=false`
- `performance_interpretation_performed=false`
- `source_runtime_modified=false`

停止原因はsource data異常ではない。BCR01 v1.0.0が、必要列集合ではなくSQLite物理列順をfresh schema順と完全一致比較した実装事故である。

active DBはmigrationで`event_key_origin`と`worker_raw_json_origin`が末尾追加されている。22必須列はすべて存在し、欠落・未知列はない。

## 8. BCR01 v1.0.1修正

修正rule:

`REQUIRE_EXACT_COLUMN_SET_ALLOW_PHYSICAL_ORDER_DIFFERENCE_EXPORT_USING_FROZEN_LOGICAL_ORDER`

- 必須列集合の完全一致を要求
- 欠落列は拒否
- 未知列は拒否
- 重複列は拒否
- 列数差は拒否
- 物理順差はmanifestへ記録
- exportは固定論理順を明示SELECT

安全契約は不変。

- SQLite `mode=ro`
- `PRAGMA query_only=ON`
- outcome table非query
- Collector/M7C無変更
- candidate formula非作成
- performance非評価

修正script commit:

`81ce359f919fba7b174ce2f8c5c25429b934ef2e`

regression test commit:

`0da97025d2f2cef5b98f51523da9ffc98e3223a8`

4 tests passed:

- fresh order
- migrated active-DB order
- bad payload SHA fail-closed
- unexpected column fail-closed

## 9. 現在の唯一の次作業

v1.0.1をpullし、同じBATを1回だけ実行する。

Repository:

`C:\btc-ff`

Branch:

`feature/btc-fresh-forward-research`

BAT:

`C:\btc-ff\scripts\btc_ml_v1\BCR01_outcome_blind_source_snapshot\01_run_BCR01.bat`

提出ZIP:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR01_outcome_blind_source_snapshot\LATEST\99_UPLOAD_PACKAGE.zip`

初回runは実装事故によりsnapshot未作成だったため、この置換runだけが追加承認されている。v1.0.1 pull後に1回実行し、成功・失敗を問わず最初のZIPを提出する。それ以上繰り返さない。

## 10. 現在禁止

- raw SQLite/WAL/SHM upload
- BCR01 v1.0.1を複数回実行
- event ledger実装
- candidate formula設計
- WR/PF/DD/MFE/MAE評価
- FF06作成
- shadow/runtime/live昇格
- Discord送信
- MT5発注
- Collector/M7C/M8C/M9/M10の停止・変更
- GOLD/MOCHIPOYO側へのBTC結果書込み

## 11. 次のZIP受領時

成功ZIPなら10ファイルを全監査する。

- exact ZIP layout
- status READY
- v1.0.1
- exact column sets
- migrated physical order記録
- fixed export order
- cursor=max raw ID
- raw ID/event key uniqueness
- payload SHA parity
- source identity parity
- no annotation orphan
- no cursor regression
- forbidden export zero
- `outcomes_opened=false`
- `performance_interpretation_performed=false`

error ZIPなら、exact errorを診断し、再実行を先に依頼しない。

## 12. runtime保護

Collector、M7C、M8C、M9、M10は起動状態を維持し、停止・再起動・初期化・変更しない。

## 13. fail-closed

branch、固定入口、latest handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
