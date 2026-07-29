# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_D1_COMPLETE_BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT_READY`
- updated: `2026-07-30T07:01:00+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_D1_COMPLETE_BCR01_OUTCOME_BLIND_SNAPSHOT_READY_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_D1_COMPLETE_BCR01_OUTCOME_BLIND_SNAPSHOT_READY_20260730.md`
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

MOCHIPOYO branchの一般探索は禁止。D1でexact pathとして許可・監査されたM7C/Collector契約ファイルとユーザー提出物だけを読み取り専用で扱う。

## 5. 研究目的

- Track A: M7C/Collectorの実source alertを一次証拠にする、もちぽよ由来BTC候補
- Track B: もちぽよと異なる相場原理の独立ベクトルBTC候補

完全複製や単発バックテストではなく、将来の収益性、安定性、損失制御、候補間補完性、shadow parity、drift監視、fail-closed停止まで含むシステムを作る。

## 6. 現在の到達点

D1のM7C・Collector監査は完了。

- M7C supported source events: 90
- supported BTCUSD: 51
- Collector combined cycles: 12,612
- Collector inserted rows: 127
- duplicate rows: 0
- latest observed cursor: 189
- performance interpretation: not performed

## 7. 現在の次作業

`BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT`

ユーザーは次を1回だけ実行する。

`scripts/btc_ml_v1/BCR01_outcome_blind_source_snapshot/01_run_BCR01.bat`

提出ZIP:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR01_outcome_blind_source_snapshot\LATEST\99_UPLOAD_PACKAGE.zip`

raw SQLite DB、WAL、SHMは送らない。BCR01はallowlisted source tablesだけをread-only transactionで論理exportする。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 9. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
