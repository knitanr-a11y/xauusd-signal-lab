# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR09_COMPLETE_NO_SUPPORTED_BASE_MACHINE_BCR10_DIAGNOSTIC_NEXT`
- updated: `2026-07-30T20:00:00+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR09_VALUE_GATE_COMPLETE_BCR10_PATH_DIAGNOSTIC_NEXT_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR09_VALUE_GATE_COMPLETE_BCR10_PATH_DIAGNOSTIC_NEXT_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR09_CORRECTED_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr09_corrected_shared_retrospective_value_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR09_PREACCEPTANCE_COMMON_WARMUP_INCIDENT_AND_CORRECTION_20260730.md`
9. `docs/btc_ml_v1/BTC_BCR09_SHARED_EXECUTION_COST_AND_RETROSPECTIVE_VALUE_GATE_CONTRACT_20260730.md`
10. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_RESULT_20260730.md`
11. `docs/btc_ml_v1/BTC_BCR08A_KIWAMI_COMMISSION_CONTRACT_RESOLUTION_20260730.md`
12. `docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_CONTRACT_20260730.md`
13. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
14. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
15. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
16. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

MOCHIPOYOの一般探索は禁止。current policyでexact allowlistされたM7C/Collector証拠と固定SHA提出物だけを読み取り専用で扱う。

## 5. BCR09正式結果

8つの凍結済み完全state machineを同一execution/cost契約で評価した。

- accepted package SHA: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- closed trades: `8,474`
- supported: `0`
- promising: `0`
- hold/cost-sensitive: `1`
- rejected: `7`
- deployable candidates: `0`
- portfolio: none
- shadow: not started

B4 E0だけC0でPF `1.0006`、net `+108.97`だったが、C2でPF `0.9497`、net `-8,951.03`となるためHOLD。その他はbaseでreject。

最初のwarm-up不一致runは無効な監査履歴。corrected runだけを使う。

## 6. 重要な解釈境界

Track AとB4のsame-server-date subsetは正だったが、これは未来のexit日付を使った分類であり、採用済みfilterではない。

swapは未計上なので、rollover-exposed損失をswapだけのせいにしない。価格path、保有長、時間帯、financingを分離して調べる。

B1はsame-server-dateでも負のため、現在のrescue対象から外す。

## 7. 現在の次作業

`BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC`

Track A F1〜F4とB4 E0/E1だけを対象に、固定した保有本数bin、日付跨ぎbin、4時間server-time bin、MFE/MAE/givebackを診断する。

BCR10では次をしない。

- time stopや23:45 flatのPnL評価
- TP/SL、trailing stop探索
- ATR、時刻、曜日、方向filterの採用
- 候補選定、portfolio、shadow開始

現在ユーザーの追加ファイルやBAT実行は不要。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 9. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。