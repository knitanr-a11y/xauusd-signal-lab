# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR16_COMPLETE_EIGHT_OF_EIGHT_B5_MACHINES_PASS_CAPABILITY_BCR17_AUTHORIZATION_PENDING`
- updated: `2026-07-31T00:33:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR16_COMPLETE_EIGHT_OF_EIGHT_PASS_BCR17_AUTHORIZATION_PENDING_20260731.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR16_COMPLETE_EIGHT_OF_EIGHT_PASS_BCR17_AUTHORIZATION_PENDING_20260731.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR16_B5_OUTCOME_BLIND_CAPABILITY_RESULT_20260731.md`
7. `configs/btc_ml_v1/btc_bcr16_b5_outcome_blind_capability_result_20260731.json`
8. `docs/btc_ml_v1/BTC_BCR16_B5_OUTCOME_BLIND_CAPABILITY_IMPLEMENTATION_READY_20260731.md`
9. `configs/btc_ml_v1/btc_bcr16_b5_outcome_blind_capability_implementation_ready_20260731.json`
10. `docs/btc_ml_v1/BTC_BCR15_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM_DESIGN_CONTRACT_20260731.md`
11. `configs/btc_ml_v1/btc_bcr15_causal_h1_impulse_m15_pullback_reclaim_design_contract_20260731.json`
12. `docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_RESULT_20260730.md`
13. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
14. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

この順番より前にrepo全体検索、code search、古いhandoff探索をしない。

## 4. startup denylist

このBTC研究の入口として次を読まない・使わない。

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

MOCHIPOYOの一般探索は禁止。Collector/M7C/M8C/M9/M10を停止・再起動・変更しない。

## 5. 現在地

BCR13/B3:

- capability pass: `0/8`
- status: `CLOSED_NO_CAPABILITY_SURVIVOR_NO_RESCUE`
- BCR14: not applicable

BCR15/BCR16/B5:

- family: `B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM`
- frozen machines: `8`
- deterministic capability package accepted
- capability pass: `8/8`
- entries/closed: `82–131`
- LONG/SHORT: `42–67 / 40–66`
- entry months: `11`
- p90 holding: `32` bars
- occupancy: `3.87%–5.68%`
- B5 return/win-loss/PF/PnL/MFE/MAE: unopened
- promoted/deployable candidates: `0`

## 6. 手ごたえ

候補-levelの能力面では初めて明確な手ごたえが出た。十分な密度、方向バランス、月分散、有限holding、低occupancyを8 machinesすべてが満たした。

ただし損益の手ごたえは未確認。structural success/failureはstate-machine終了区分であり、win/lossではない。

## 7. 現在の次作業

推奨stage:

`BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE`

BCR17は未承認。明示承認前にreturn、win/loss、PF、PnL、MFE、MAEを開かない。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

Discord、MT5発注、portfolio、prospective start、shadow、live-ready、final signalは未承認。

## 9. fail-closed

branch、最新版handoff、current state、next action、BCR15 contract、BCR16 resultが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
