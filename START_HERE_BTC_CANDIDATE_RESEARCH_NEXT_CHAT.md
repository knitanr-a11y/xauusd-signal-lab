# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR05B_ENTRY_FIDELITY_COMPLETE_BCR05C_EXIT_STATE_NEXT`
- updated: `2026-07-30T13:46:00+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR05B_ENTRY_FIDELITY_COMPLETE_BCR05C_EXIT_STATE_NEXT_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_BCR05B_ENTRY_FIDELITY_COMPLETE_BCR05C_EXIT_STATE_NEXT_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR05B_OUTCOME_BLIND_FINITE_ENTRY_GRAMMAR_RESULT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr05b_outcome_blind_finite_entry_grammar_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR05C_OUTCOME_BLIND_EXIT_AND_STATE_SIGNATURE_CONTRACT_20260730.md`
9. `configs/btc_ml_v1/btc_bcr05c_outcome_blind_exit_state_signature_contract_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR05A_OUTCOME_BLIND_TRACK_A_SOURCE_SIGNATURE_RESULT_20260730.md`
11. `docs/btc_ml_v1/BTC_BCR05A_LABEL_DERIVED_EVENT_DISTANCE_INCIDENT_AND_CORRECTION_20260730.md`
12. `docs/btc_ml_v1/BTC_BCR04_OUTCOME_BLIND_DECISION_UNIVERSE_RESULT_20260730.md`
13. `docs/btc_ml_v1/BTC_BCR03_M7C_SELECTED_BAR_GAP_BRIDGE_ADDENDUM_20260730.md`
14. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
15. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

## 5. 現在の到達点

BCR01〜BCR05B完了。outcomeは未参照。

- BCR04 decision rows: 907
- primary LONG / SHORT: 16 / 10
- eligible IDLE controls: 438
- valid LONG / SHORT exits: 17 / 10
- eligible ACTIVE_LONG / ACTIVE_SHORT controls: 223 / 168
- BCR05A corrected package SHA: `b49b9118d0e15184d8b7aea3452b70899ed0406b82360580fd076ae972d9255b`
- BCR05B package SHA: `525be07cab36d9582637a5db523d16f876a4d7cc06b1103bfdc14b29dcec65c9`
- advanced entry-fidelity variants: LONG 2、SHORT 3
- profitability candidates selected: 0

## 6. 現在の次作業

`BCR05C_OUTCOME_BLIND_EXIT_AND_STATE_SIGNATURE_ANALYSIS`

LONG EXIT 17件対ACTIVE_LONG control 223件、SHORT EXIT 10件対ACTIVE_SHORT control 168件を分離比較する。

exact、1本遅れ、missed、事前state divergenceを別分類し、state divergence中に遭遇した後続primaryをevent ID・時刻だけで追跡する。将来価格、勝敗、MFE、MAE、TP/SLは使用しない。

## 7. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 8. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
