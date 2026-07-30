# BTC候補研究 次チャット完全引き継ぎ

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T12:14:16+09:00`
- status: `BTC_REDESIGN_BCR02_CANONICAL_LEDGER_COMPLETE_BCR03_CANDLE_MAPPING_NEXT`
- authority: `LATEST_DATED_HANDOFF`

## 0. 固定入口

新チャットは必ずrepo直下の次を最初に読む。

`START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`

固定入口が本handoffを唯一の最新版として指していることを確認する。旧handoffは`AUDIT_HISTORY_ONLY`。

## 1. branch hard gate

必ず明示指定するbranch:

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branchまたは文書が矛盾する場合は停止する。

## 2. startup denylist

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
- FF05 recovery V3〜V11の実行再開資料
- 固定入口から参照されない旧state、next action、handoff

MOCHIPOYO branchの一般探索は禁止。D1でexact pathとして許可されたM7C/Collector契約ファイルと、ユーザー提出済み証拠だけを読み取り専用で扱う。M7C、Collector、M8C、M9、M10を停止・再起動・変更しない。

## 3. 最終目的

BTCUSDで将来使える候補システムを二系統で作る。

### Track A — もちぽよ由来

M7C/Collectorの実source alertを一次証拠とし、source fidelityとBTC valueを分離する。完全複製より収益性・安定性・損失制御を優先するが、再現できない部分を再現成功と偽らない。

### Track B — 独立ベクトル

もちぽよのRCI/EMA/state条件の微調整ではない異なる相場原理から候補を作る。最終的に発火重複、損益相関、共同DD、regime補完性を評価する。

## 4. 完了済みD1

### M7C一次証拠

提出ZIP SHA256:

`870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`

- source comparison rows: 125
- supported source events: 90
- supported BTCUSD: 51
- proxy decisions: 1557
- proxy signals: 168
- finalized extras: 104
- prospective start: `2026-07-20T14:54:15Z`
- outcome fields: none

### Collector証拠

提出ZIP SHA256:

`b65ddd0b7c240d5acd26c271b228142929574d82ad5e96eadec1e1f37d62b3fe`

- combined cycles: 12612
- successful: 12606
- failed: 6
- inserted source rows at that audit: 127
- duplicate insertions: 0
- all six Cloudflare failures retried from the preserved cursor

## 5. BCR01

### v1.0.0事故

初回error ZIP SHA256:

`47c38b81a465f1fa9adfbcd7901644cca8d3ab4f03f71cb9dd7353b368b602f1`

原因はSQLite物理列順をfresh schema順と一致要求した実装事故。source snapshot未作成、outcome未参照。監査履歴のみ。

### v1.0.1正式成功

提出:

`99_UPLOAD_PACKAGE(102).zip`

SHA256:

`bc562948ee8baefba32d0e291a54341243da4684bdbf43d652676d5fcdab5611`

Snapshot:

`BCR01_20260730T030649Z_RAWMAX194`

Accepted:

- exact 10-file layout
- raw rows: 194
- raw IDs: contiguous 1–194
- last successful cursor: 194
- duplicate IDs/event keys: 0
- payload SHA mismatch: 0
- source JSON identity mismatch: 0
- cursor regression: 0
- annotation orphan: 0
- outcome tables read: false
- outcomes opened: false
- performance interpretation: false

Raw ID 1 is the user-confirmed connection test and is excluded from research state.

Authoritative audit:

- `docs/btc_ml_v1/BTC_BCR01_V101_OUTCOME_BLIND_SOURCE_SNAPSHOT_AUDIT_20260730.md`
- `configs/btc_ml_v1/btc_bcr01_v101_outcome_blind_source_snapshot_result_20260730.json`

## 6. BCR02 canonical source event ledger

BCR01 raw events were replayed through a deterministic state machine after excluding connection-test ID 1.

Output package SHA256:

`5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`

Research scope:

- prospective start: `2026-07-20T14:54:15Z`
- research raw IDs: 64–194
- rows: 131
- BTCUSD: 76
- XAUUSD: 55
- supported BTCUSD primary/valid-exit events: 53
- supported XAUUSD: 39

M7C parity against IDs 64–188:

- comparison rows: 125
- ticker/time/state/transition/role exact match: 125/125
- mismatches: 0

Transition counts through ID 194:

- PRIMARY_LONG 25
- PRIMARY_SHORT 21
- LONG_EXIT 26
- SHORT_EXIT 20
- REENTRY_LONG 13
- REENTRY_SHORT 10
- OPPOSITE_ALERT_IGNORED 9
- OPPOSITE_EXIT_IGNORED 7

No outcome or performance field was opened.

Authoritative files:

- `docs/btc_ml_v1/BTC_BCR02_CANONICAL_SOURCE_EVENT_LEDGER_20260730.md`
- `configs/btc_ml_v1/btc_bcr02_canonical_source_event_ledger_result_20260730.json`
- `scripts/btc_ml_v1/BCR02_canonical_source_event_ledger/python/run_bcr02_canonical_source_event_ledger.py`
- `tests/btc_ml_v1/test_bcr02_canonical_source_event_ledger.py`

## 7. BCR02A重要所見

BTC primary source alerts 25件について、exact source timeのM7C featuresを監査した。

- correct RCI turn direction: 25/25
- correct EMA stack: 22/25
- M7C exact match: 14
- M7C missed: 11
- missedのうちproxy/source state divergence: 9
- missedのRCI turn mismatch: 0

入口特徴が全く違うのではなく、以前のexit/entry不一致によりproxy stateがずれ、後続primaryを連鎖的にrejectしている可能性が強い。

BTC exits 26件:

- exact: 13
- one bar late: 6
- missed: 7
- exact source timeでM7C threshold pass: 16/26

したがってTrack Aではentry triggerとexit/state resynchronizationを別仮説として扱う。まだ収益性は結論しない。

Document:

`docs/btc_ml_v1/BTC_BCR02A_M7C_FIDELITY_DECOMPOSITION_OUTCOME_BLIND_20260730.md`

## 8. 現在の次作業

`BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_AND_FEATURE_AVAILABILITY_AUDIT`

目的:

- TradingView/VANTAGE BTC source `bar_time_utc`をMT5 server-openへ対応
- observed UTC+3 mappingを検証
- source priceとMT5価格のfeed差を監査
- decision時点で利用可能なclosed M15とcurrent openを固定
- current high/low/close、future bar、outcomeを禁止

Contract:

`docs/btc_ml_v1/BTC_BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_CONTRACT_20260730.md`

## 9. ユーザーから次に必要な証拠

M7C/BTC環境で現在使用している正確な次のファイルを、編集せず1つのZIPへ入れて提出する。

`btcusdsharp_m15.csv`

元のファイル名を維持する。M7C/Collectorは停止・再起動しない。GOLD CSVは送らない。

同名ファイルが複数存在する場合は、更新日時だけで選ばず、まず候補のフルパスを提示する。権威sourceを明示解決するまでCSVを採用しない。

## 10. まだ禁止

- candidate formula freeze
- outcome開示
- WR/PF/DD/MFE/MAE
- TP/SL最適化
- FF06
- shadow runtime
- Discord
- MT5 order
- lot設計
- GOLD/MOCHIPOYO monitor変更

## 11. 新チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/btc-fresh-forward-research

BTC候補研究の続きです。
最初にrepo直下のSTART_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.mdを読み、そこに記載された最新版handoffと必須read orderだけを順番どおり読んでください。
main、default branch、AGENTS.md、GOLD系、旧BTC handoff、FF05 recovery、MOCHIPOYO branchの一般探索は禁止です。
現在はBCR02 canonical ledger完了、次はBCR03 BTC source-to-MT5 candle mappingです。
推測・fallbackは禁止し、M7C/Collector/M8C/M9/M10を停止・変更しないでください。
```
