# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR02_CANONICAL_LEDGER_COMPLETE_BCR03_CANDLE_MAPPING_NEXT`
- updated: `2026-07-30T12:14:16+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR02_LEDGER_COMPLETE_BCR03_CANDLE_MAPPING_NEXT_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR02_LEDGER_COMPLETE_BCR03_CANDLE_MAPPING_NEXT_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR01_V101_OUTCOME_BLIND_SOURCE_SNAPSHOT_AUDIT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr01_v101_outcome_blind_source_snapshot_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR02_CANONICAL_SOURCE_EVENT_LEDGER_20260730.md`
9. `configs/btc_ml_v1/btc_bcr02_canonical_source_event_ledger_result_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR02A_M7C_FIDELITY_DECOMPOSITION_OUTCOME_BLIND_20260730.md`
11. `docs/btc_ml_v1/BTC_BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_CONTRACT_20260730.md`
12. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
13. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

この順番より前にrepo全体検索、code search、古いhandoff探索をしない。

## 4. startup denylist

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
- 本入口から参照されない旧state、next action、handoff

MOCHIPOYO branchの一般探索は禁止。D1でexact pathとして許可されたM7C/Collector契約ファイルとユーザー提出物だけを読み取り専用で扱う。

## 5. 研究目的

- Track A: M7C/Collectorの実source alertを一次証拠にする、もちぽよ由来BTC候補
- Track B: もちぽよと異なる相場原理の独立ベクトルBTC候補

完全複製や単発バックテストではなく、将来の収益性、安定性、損失制御、候補間補完性、shadow parity、drift監視、fail-closed停止まで含むシステムを作る。

## 6. 現在の到達点

BCR01 v1.0.1 source snapshotとBCR02 canonical source event ledgerは完了。

- BCR01 raw rows: 194、IDs 1–194、cursor 194
- BCR01 outcome tables read: false
- BCR02 research rows: 131、IDs 64–194
- BCR02 BTCUSD rows: 76
- BCR02 BTC supported primary/valid-exit events: 53
- M7C parity IDs 64–188: 125/125 exact
- performance interpretation: not performed

## 7. 現在の次作業

`BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_AND_FEATURE_AVAILABILITY_AUDIT`

次に必要な証拠:

`btcusdsharp_m15.csv`

M7C/BTC環境で現在使用している正確なファイルを、元ファイル名のまま1つのZIPへ入れて提出する。M7C/Collectorを停止・再起動・編集しない。GOLD CSVは送らない。

同名ファイルが複数存在する場合は、更新日時だけで選ばず、候補のフルパスを先に提示する。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 9. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
