# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR13_IMPLEMENTATION_READY_FROZEN_INPUT_LOCAL_RUN_PENDING_NO_OUTCOME_OPENED`
- updated: `2026-07-30T22:11:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR13_IMPLEMENTATION_READY_LOCAL_RUN_PENDING_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR13_IMPLEMENTATION_READY_LOCAL_RUN_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_IMPLEMENTATION_READY_20260730.md`
7. `configs/btc_ml_v1/btc_bcr13_b3_outcome_blind_density_implementation_ready_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN_CONTRACT_20260730.md`
9. `configs/btc_ml_v1/btc_bcr12_materially_new_outcome_blind_track_b_mechanism_design_contract_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_RESULT_20260730.md`
11. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_result_20260730.json`
12. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_CONTRACT_20260730.md`
13. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_development_contract_20260730.json`
14. `docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_RESULT_20260730.md`
15. `configs/btc_ml_v1/btc_bcr10_holding_rollover_path_diagnostic_result_20260730.json`
16. `docs/btc_ml_v1/BTC_BCR09_CORRECTED_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260730.md`
17. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_RESULT_20260730.md`
18. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
19. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
20. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
21. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

MOCHIPOYOの一般探索は禁止。current policyでexact allowlistされたM7C/Collector証拠だけを読み取り専用で扱う。

## 5. BCR13正式到達点

- family: `B3_BREAKOUT_RETEST_REACCELERATION`
- frozen machines: `8`
- implementation: created
- synthetic/exact-path tests: `6 passed`
- actual frozen 30,661-row run: pending
- B3 return/win-loss/PF/PnL/MFE/MAE: unopened
- promoted/deployable candidate: `0`

実装は完全確定済みM15バーだけを使い、current bar high/low/close、未来結果、fallback、補間、H1/H4/D1、source stateを使用しない。

## 6. 現在の次作業

ユーザーのWindows環境で次を実行する。

`scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/01_run_BCR13.bat`

成功後、次をアップロードする。

1. `BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip`
2. `deterministic_repeat.json`
3. `package_sha256.txt`

BAT失敗時は完全なconsole errorを提示する。別CSV、SHA変更、row count変更、類似ファイルfallbackは禁止。

## 7. BCR14境界

BCR14 value evaluationは未承認。BCR13 packageの受領・監査前に、return、win/loss、PF、PnL、MFE、MAE、portfolio、prospective start、shadowへ進まない。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

Discord、MT5発注、prospective start、shadow、live-ready、final signalは未承認。

## 9. fail-closed

branch、最新版handoff、current state、next action、BCR12契約、BCR13 implementation readinessが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
