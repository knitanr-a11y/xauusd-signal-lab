# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR03_CONTENT_CLOCK_FEATURE_PARITY_COMPLETE_ORIGINAL_PATH_PENDING`
- updated: `2026-07-30T12:42:00+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR03_CONTENT_PARITY_ACCEPTED_ORIGINAL_PATH_PENDING_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR03_CONTENT_PARITY_ACCEPTED_ORIGINAL_PATH_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR03_M15_CONTENT_CLOCK_AND_M7C_FEATURE_PARITY_AUDIT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr03_m15_content_clock_feature_parity_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_CONTRACT_20260730.md`
9. `docs/btc_ml_v1/BTC_BCR02_CANONICAL_SOURCE_EVENT_LEDGER_20260730.md`
10. `docs/btc_ml_v1/BTC_BCR02A_M7C_FIDELITY_DECOMPOSITION_OUTCOME_BLIND_20260730.md`
11. `docs/btc_ml_v1/BTC_BCR01_V101_OUTCOME_BLIND_SOURCE_SNAPSHOT_AUDIT_20260730.md`
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

MOCHIPOYO branchの一般探索は禁止。D1でexact pathとして許可されたM7C/Collector契約ファイルと、固定SHAのユーザー提出物だけを読み取り専用で扱う。

## 5. 研究目的

- Track A: M7C/Collectorの実source alertを一次証拠にする、もちぽよ由来BTC候補
- Track B: もちぽよと異なる相場原理の独立ベクトルBTC候補

完全複製や単発バックテストではなく、将来の収益性、安定性、損失制御、候補間補完性、shadow parity、drift監視、fail-closed停止まで含むシステムを作る。

## 6. 現在の到達点

BCR01、BCR02、BCR02A、BCR03の内容・時刻・feature parity監査まで完了。

- BCR01 raw rows: 194、cursor 194、outcome table未参照
- BCR02 BTCUSD source rows: 76
- BCR02 BTC supported primary/valid-exit: 53
- M7C state parity: 125/125
- 提出M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- M15 rows: 30,661
- BTC event current/previous bar mapping: 76/76
- M7C BTC RCI9/EMA parity: 890/890
- performance interpretation: not performed

## 7. 現在の次作業

追加CSVやBATではない。

ユーザーに、提出したCSVをコピーした**元のWindowsフルパス**をそのまま貼ってもらう。

例は推測に使わない。ファイル名、更新日時、MetaQuotesの慣例からpathを補わない。

pathが一意で今回の提出物の役割と整合すればBCR03 provenanceを閉じ、その後に次のoutcome-blind候補grammar設計契約を作る。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 9. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
