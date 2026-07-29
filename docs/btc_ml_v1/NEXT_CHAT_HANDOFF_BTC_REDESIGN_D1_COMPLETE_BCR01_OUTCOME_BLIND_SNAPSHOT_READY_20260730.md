# BTC候補研究 次チャット完全引き継ぎ — D1完了 / BCR01実行待ち

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T07:01:00+09:00`
- status: `BTC_REDESIGN_D1_COMPLETE_BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT_READY`
- authority: `LATEST_DATED_HANDOFF`

## 0. 固定入口

必ず最初にrepo直下の次を読む。

`START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`

固定入口が本ファイルを唯一の最新版handoffとして指していることを確認する。古いhandoffは`AUDIT_HISTORY_ONLY`。

## 1. branch hard gate

必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branchまたは文書が矛盾する場合は停止する。

## 2. 最初に読む順番

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. 本handoff
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_D1_M7C_PRIMARY_EVIDENCE_PACKAGE_AUDIT_20260730.md`
7. `configs/btc_ml_v1/btc_d1_m7c_primary_evidence_manifest_20260730.json`
8. `docs/btc_ml_v1/BTC_D1B_COLLECTOR_LOG_AND_CODE_AUDIT_20260730.md`
9. `configs/btc_ml_v1/btc_d1b_collector_evidence_manifest_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT_CONTRACT_20260730.md`
11. `configs/btc_ml_v1/btc_bcr01_outcome_blind_source_snapshot_contract_20260730.json`
12. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
13. `configs/btc_ml_v1/btc_candidate_research_redesign_contract_20260730.json`
14. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

この順番の前にrepo全体検索、GOLD/MOCHIPOYO横断探索、旧BTC handoff探索をしない。

## 3. 読んではいけないもの

BTC研究の入口として次を使用しない。

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
- FF05 recovery V3〜V11の再開資料
- 固定入口から参照されない旧state、next action、handoff

MOCHIPOYO branchの一般探索は禁止。D1でexact pathとして監査したCollector契約ファイル以外を勝手に追加参照しない。

## 4. 最終目的

BTCUSDで将来使える可能性があるトレード候補システムを作る。

- Track A: M7C/Collectorの実source alertを一次証拠にする、もちぽよ由来研究
- Track B: もちぽよとは異なる相場原理の独立ベクトル研究

完全複製や単一バックテストの見栄えではなく、収益性、安定性、損失制御、候補間補完性、shadow parity、drift監視、fail-closed停止まで扱う。

## 5. D1 M7C一次証拠監査

ユーザー提出ZIP SHA256:

`870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`

到達点:

- source comparison rows: 125
- supported source events: 90
- supported BTCUSD: 51
- supported XAUUSD: 39
- proxy decisions: 1557
- proxy signals: 168
- finalized extras: 104
- observed MT5 server offset: UTC+3
- outcome fields: none in submitted artifacts
- performance interpretation: not performed

M7C prospective start remains `2026-07-20T14:54:15Z`.

## 6. D1B Collector監査

ユーザー提出ZIP SHA256:

`b65ddd0b7c240d5acd26c271b228142929574d82ad5e96eadec1e1f37d62b3fe`

Log totals:

- two Collector loop runs
- combined cycles: 12,612
- successful: 12,606
- failed: 6
- response rows: 127
- inserted rows: 127
- duplicate rows: 0
- latest cursor: 189

6 failuresはすべてCloudflare HTTP 500 / Error 1101。全件でcursorは進まず、次cycleが同じcursorから回収した。cursor regressionやduplicate insertionはない。

`latest_collection_error.json`は古いエラーが残るdiagnostic freshness defectを持つため、単独では現在状態の権威にしない。Collector本体のdata loss証拠ではない。D1中はCollector codeを変更していない。

## 7. Source timestamp/provenance contract

`raw_alerts`は少なくとも次を保存する。

- `cloudflare_id`
- `event_key` / origin
- `received_at_utc`
- `bar_time_utc`
- `fired_at_utc`
- `downloaded_at_utc`
- source / strategy / event / ticker / timeframe / exchange
- OHLC / message when present
- `worker_raw_json`
- exact `collector_source_row_json`
- `payload_sha256`

既存ID/event keyに異なるpayloadが来た場合はimmutable collisionとしてtransaction rollbackする。cursorとinsertは同一transactionで更新される。

## 8. 生SQLite DBを送ってはいけない理由

DB schemaにはsource tablesだけでなく、`virtual_entries`と`outcomes`等の結果tableもある。したがってraw DB、WAL、SHMのcopy/uploadは禁止。

BCR01は次の4tableだけを論理exportする。

- `collector_state`
- `raw_alerts`
- `raw_alert_annotations`
- `collection_runs`

次をquery/exportしない。

- `episodes`
- `episode_events`
- `episode_build_anomalies`
- `episode_build_runs`
- `mt5_alignment`
- `feature_snapshots`
- `virtual_entries`
- `outcomes`

## 9. 現在の正式状態

`BTC_REDESIGN_D1_COMPLETE_BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT_READY`

D1のM7C・Collector inventory、clock/provenance/schema確認、outcome exposure判定は完了した。

現在はBCR01を1回実行し、immutableなoutcome-blind raw source snapshotを取得する段階。

## 10. BCR01実行入口

フォルダ:

`scripts/btc_ml_v1/BCR01_outcome_blind_source_snapshot`

実行BAT:

`01_run_BCR01.bat`

source:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3`

output:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR01_outcome_blind_source_snapshot\LATEST\99_UPLOAD_PACKAGE.zip`

BCR01はSQLiteを`mode=ro`かつquery-onlyで開き、一つのconsistent read transactionを使用する。Collector/M7Cは停止・再起動・変更しない。BTC output root以外へ書き込まない。

## 11. BCR01完了後に行う監査

- ZIP layoutと各SHA
- exact schema
- raw ID/event key uniqueness
- payload SHA256 parity
- source JSON identity parity
- cursor=max raw ID
- annotation handling
- collection run chronology
- BTCUSD raw event数とtimestamp distribution
- `bar_time` / `fired_at` / `received_at` / `downloaded_at` lag
- exchange/timeframe/source-price identifier
- connection-test除外
- outcome table非読取り証拠

その後に初めて、Track A event ledgerとTrack B用データ契約を設計する。

## 12. 現在禁止

- raw SQLite DB/WAL/SHM upload
- BCR01を複数回実行
- candidate formula設計
- WR/PF/DD/MFE/MAE分析
- outcome table読取り
- FF06作成
- shadow/live/Discord/MT5 order/lot設計
- Collector、M7C、M8C、M9、M10の停止・変更
- GOLD/MOCHIPOYO側へのBTC結果書込み

## 13. 次チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/btc-fresh-forward-research

BTC候補研究の続きです。
最初にrepo直下の次だけを読み、そこに指定された最新版handoffとread orderへ従ってください。

START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md

main/default branch、AGENTS.md、GOLD、旧BTC handoff、FF05 recovery、MOCHIPOYO branchの一般探索は禁止です。
現在はD1完了、BCR01 outcome-blind source snapshotの1回実行待ちです。
```
