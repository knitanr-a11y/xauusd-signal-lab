# BTC候補研究 次チャット完全引き継ぎ

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T06:49:00+09:00`
- status: `BTC_REDESIGN_D1_M7C_PRIMARY_EVIDENCE_AUDITED_COLLECTOR_PROVENANCE_PENDING_READ_ONLY`
- authority: `LATEST_DATED_HANDOFF`

## 0. 固定入口

必ず最初に読む:

`START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`

この文書が固定入口から唯一の最新版handoffとして参照されていることを確認する。

必ずbranchを明示する:

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、古いhandoff、会話記憶、似たファイルへのfallbackは禁止する。

## 1. 読む順番

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_D1_M7C_PRIMARY_AUDITED_COLLECTOR_PROVENANCE_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_D1_M7C_PRIMARY_EVIDENCE_PACKAGE_AUDIT_20260730.md`
7. `configs/btc_ml_v1/btc_d1_m7c_primary_evidence_manifest_20260730.json`
8. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
9. `configs/btc_ml_v1/btc_candidate_research_redesign_contract_20260730.json`
10. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

上記を読む前にrepo全体検索、GOLD探索、MOCHIPOYO一般探索、候補コード探索をしない。

## 2. 読んではいけないもの

BTC研究の入口として使用禁止:

- `AGENTS.md` — 現在GOLD_ML_V1用
- `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
- `docs/gold_v3/**`
- `docs/gold_ml_v1/**`
- `config/gold_v3/**`
- `config/gold_ml_v1/**`
- `scripts/gold_v3/**`
- `scripts/gold_ml_v1/**`
- GOLD V2、旧GOLD、GOLD V3、DISC8、Stage41
- 旧BTC stacking / YouTube候補handoff
- FF05 recovery V3〜V11の実行再開資料
- 固定入口から参照されていない旧current state、旧next action、旧handoff

MOCHIPOYO branchを一般検索しない。現在許可されるのは、最新版handoffが正確に列挙したM7C/Collectorの契約文書、forced-reboot契約、またはユーザー提出物だけである。

## 3. ユーザーの最終目的

BTCUSDで将来使用できる可能性のある、検証・shadow・監視・停止まで含んだ候補システムを作る。

### Track A — もちぽよsource-anchored

- M7C・Collectorに記録された実source alertを一次証拠にする。
- 発火場所を見ずにRCIやEMAから想像だけで作らない。
- source fidelityとBTC valueを分離する。
- source matched、missed source、extra candidateを混ぜない。
- 完全複製よりBTCでの収益性、安定性、損失制御を優先できる。
- ただし再現失敗を再現成功と偽らない。

### Track B — independent vector

- もちぽよ条件のパラメータ違いではない。
- trend continuation、compression-expansion、breakout-retest、mean reversion、方向非対称など異なる相場原理を使う。
- Track Aとの発火・損益相関、共同DD、相場regimeごとの補完性を評価する。

## 4. 今回受領したD1 M7C資料

User ZIP:

`新しい圧縮された (ZIP) フォルダー.zip`

SHA256:

`870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`

必要7ファイルすべてと、追加の`m7c_runtime_start_receipt.json`を受領した。

正式監査:

- `docs/btc_ml_v1/BTC_D1_M7C_PRIMARY_EVIDENCE_PACKAGE_AUDIT_20260730.md`
- `configs/btc_ml_v1/btc_d1_m7c_primary_evidence_manifest_20260730.json`

このZIPはD1 manual inspection packageとして受理した。実行中sourceをbefore/after hashで固定したD2 immutable snapshotではない。

## 5. D1で確定したこと

### Runtime

- M7C status: `RUNNING / COLLECTING`
- prospective start: `2026-07-20T14:54:15Z`
- report built: `2026-07-29T21:46:15Z`
- current process started: `2026-07-23T06:36:43Z`
- cycles: `1884`
- successful: `1884`
- failed: `0`
- audit-only: true
- Discord / MT5 / live_ready / final_signal: all false

### Source and proxy inventory

- source comparison rows: `125`
- raw alert IDs: contiguous unique `64–188`
- supported source events: `90`
- BTCUSD supported: `51`
- XAUUSD supported: `39`
- exact match: `55`
- one-bar late match: `9`
- missed supported source: `26`
- unsupported REENTRY: `23`
- unsupported opposite event: `12`
- proxy decisions: `1557`
- emitted proxy signals: `168`
- finalized extra proxy signals: `104`

All JSON/CSV counts matched. No duplicate raw IDs, reused matched proxy key, orphan proxy signal or full-row duplicate was found.

These are fidelity and structural counts, not profitability results.

### Clock

All proxy decisions satisfy:

`decision_time_utc = current_server_open - 3 hours`

The observed MT5 server clock is therefore UTC+3 for this interval.

Normal selected/current M15 gap is 15 minutes for 1549 rows. Eight explicit market/data gaps exist; all emitted `NO_SIGNAL`. Do not interpolate them.

Collector receipt time and genuine source raw timestamp semantics are not present in the package and remain unresolved.

### Causality and outcome exposure

- previous fully closed M15 features only
- current M15 open only
- current high/low/close forbidden
- future bars forbidden
- trade outcomes forbidden
- submitted CSVs have no win/loss, P/L, R, PF, DD, MFE or MAE columns

No trading-performance interpretation was performed.

## 6. Log restart observation

The log contains two cycle-number sequences:

- cycles 1–619
- current cycles 1–1884 from `2026-07-23T06:36:43Z`

All logged cycle exits are zero and prospective start remained unchanged.

Exact allowed read-only reference:

`config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json`

That contract permits persistent-loop restart after forced reboot without resetting runtime manifest, prospective start or SQLite. The observed cycle reset is compatible with that design, but the actual recovery-run receipt is absent. Record as:

`COMPATIBLE_WITH_FORCED_REBOOT_RECOVERY_NOT_YET_PROVEN`

Do not stop, restart or reset M7C to investigate it.

## 7. 現在の正式状態

status:

`BTC_REDESIGN_D1_M7C_PRIMARY_EVIDENCE_AUDITED_COLLECTOR_PROVENANCE_PENDING_READ_ONLY`

decision:

`ACCEPT_M7C_PRIMARY_STRUCTURE_EVIDENCE_CONTINUE_D1_WITH_COLLECTOR_PROVENANCE`

D0とM7C一次監査は完了した。候補式や成績評価にはまだ進まない。

## 8. 現在の次アクション

次はD1のCollector側だけ:

`D1B_COLLECTOR_PROVENANCE_INVENTORY_READ_ONLY`

ユーザーから、次の既存3ファイルを1つのZIPで受け取る:

- `collector_forever.log`
- `latest_loop_status.json`
- `latest_collection_result.json`

Collector/M7Cを停止、再起動、初期化、編集しない。

確認する内容:

- Collector現在status、cycles、failures、cursor
- raw event identifierとsource payloadの所在
- collection/receipt timestamp
- duplicate、revision、replacement、late-arrival挙動
- genuine source event timestampの意味
- raw storage/database pathとschema exposure
- outcome-like fieldsの有無
- 2026-07-23 restart/recoveryの痕跡

3ファイルがSQLite/databaseを参照しても、まだDBを送らせない。先にpath・schema・必要最小範囲を確定する。

## 9. 現在禁止

- candidate formula design
- WR / PF / DD / MFE / MAE分析
- outcomeを開く
- D2 immutable snapshot実装
- event ledger実装
- new BAT
- FF06
- shadow runtime
- lot design
- Discord
- MT5 order
- live_ready
- automatic promotion
- M7C / Collector / M8C / M9 / M10停止・変更
- GOLD/MOCHIPOYO側へのBTC研究結果書込み

## 10. Collector資料受領後

同じ作業内で:

1. ZIP SHAと内部ファイルSHAを固定
2. Collector schema/status/cursor/clock/provenance監査
3. D1 source allowlistを確定またはblock
4. D1 clock/event/outcome exposure inventoryを更新
5. D2に必要な最小source snapshotを設計
6. fixed START_HERE、latest handoff、current_state、next_actionを更新
7. D2実装前にユーザーへ未決事項と選択肢を提示

## 11. 新チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/btc-fresh-forward-research

BTC候補研究の続きです。

最初に、GitHub上の次の固定入口を最初から最後まで読んでください。

START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md

固定入口が指定する最新版handoff、current_state、next_action、handoff policy、D1監査だけを順番どおり読んでください。

main/default branch、AGENTS.md、GOLD関連、古いBTC handoff、FF05 recovery、MOCHIPOYO branchの一般探索は禁止です。

現在はM7C一次証拠ZIPの監査が完了し、D1B Collector provenance用3ファイルZIP待ちです。候補式や性能評価にはまだ進まないでください。
```
