# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR17_COMPLETE_ONE_PROMISING_ONE_HOLD_SIX_REJECT_NO_SUPPORTED_BCR18_AUTHORIZATION_PENDING`
- updated: `2026-07-31T01:30:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取り・書込みは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR17_COMPLETE_ONE_PROMISING_ONE_HOLD_BCR18_AUTHORIZATION_PENDING_20260731.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR17_COMPLETE_ONE_PROMISING_ONE_HOLD_BCR18_AUTHORIZATION_PENDING_20260731.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260731.md`
7. `configs/btc_ml_v1/btc_bcr17_b5_shared_retrospective_value_gate_result_20260731.json`
8. `docs/btc_ml_v1/BTC_BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_CONTRACT_20260731.md`
9. `configs/btc_ml_v1/btc_bcr17_b5_shared_retrospective_value_gate_contract_20260731.json`
10. `docs/btc_ml_v1/BTC_BCR16_B5_OUTCOME_BLIND_CAPABILITY_RESULT_20260731.md`
11. `configs/btc_ml_v1/btc_bcr16_b5_outcome_blind_capability_result_20260731.json`
12. `docs/btc_ml_v1/BTC_BCR15_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM_DESIGN_CONTRACT_20260731.md`
13. `configs/btc_ml_v1/btc_bcr15_causal_h1_impulse_m15_pullback_reclaim_design_contract_20260731.json`
14. `docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_RESULT_20260730.md`
15. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
16. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

この順番より前にrepo全体検索、古いhandoff探索、GOLD/MOCHIPOYO一般探索をしない。

## 4. startup denylist

次をBTC研究の再開根拠にしない。

- `AGENTS.md`
- GOLD V2、旧GOLD、DISC8、Stage41
- `docs/gold_v3/**`
- `docs/gold_ml_v1/**`
- `config/gold_v3/**`
- `config/gold_ml_v1/**`
- `scripts/gold_v3/**`
- `scripts/gold_ml_v1/**`
- 旧BTC stacking / YouTube候補handoff
- FF05 recovery V3〜V11
- 本入口から参照されない旧state、next action、handoff

Collector、M7C、M8C、M9、M10を停止・再起動・変更しない。

## 5. 現在地

BCR13/B3:

- capability pass: `0/8`
- status: `CLOSED_NO_CAPABILITY_SURVIVOR_NO_RESCUE`

BCR15/BCR16/B5:

- capability pass: `8/8`
- accepted BCR16 package SHA: `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`
- closed episode rows: `844`

BCR17 value result:

- supported: `0`
- promising: `1`
- hold/cost-sensitive: `1`
- reject: `6`
- deployable candidates: `0`

Promising research survivor:

`TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM`

- trades: `107`
- C0 PF/net: `1.0495 / +1,509.24`
- C2 PF/net: `1.0079 / +245.49`
- C2 maximum drawdown: `9,803.00`
- C2 Holm-adjusted p: `1.0`
- assessment: `MODEST_FIRST_POSITIVE_SIGNAL_NOT_ROBUST`

## 6. 現在の次作業

推奨stage:

`BCR18_B5_PROMISING_SURVIVOR_PROSPECTIVE_PREREGISTRATION`

BCR18は未承認。BCR17結果アップロードはBCR18承認ではない。

明示承認前に次を行わない。

- BCR18 contract作成
- prospective boundary設定
- shadow開始
- LONG削除またはSHORT-only化
- same-server-date filter
- rollover-flat/max-holding救済
- threshold/exit変更
- candidate promotion

## 7. runtime protection

portfolio、Discord、MT5発注、live-ready、final signalは未承認。

GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 8. fail-closed

branch、最新版handoff、current state、next action、BCR17 resultが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
