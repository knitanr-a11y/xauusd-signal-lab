# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR16_B5_IMPLEMENTATION_READY_FROZEN_INPUT_LOCAL_RUN_PENDING_NO_OUTCOME_OPENED`
- updated: `2026-07-31T00:03:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR16_IMPLEMENTATION_READY_LOCAL_RUN_PENDING_20260731.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR16_IMPLEMENTATION_READY_LOCAL_RUN_PENDING_20260731.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR16_B5_OUTCOME_BLIND_CAPABILITY_IMPLEMENTATION_READY_20260731.md`
7. `configs/btc_ml_v1/btc_bcr16_b5_outcome_blind_capability_implementation_ready_20260731.json`
8. `docs/btc_ml_v1/BTC_BCR15_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM_DESIGN_CONTRACT_20260731.md`
9. `configs/btc_ml_v1/btc_bcr15_causal_h1_impulse_m15_pullback_reclaim_design_contract_20260731.json`
10. `docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_RESULT_20260730.md`
11. `configs/btc_ml_v1/btc_bcr13_b3_outcome_blind_density_and_state_machine_result_20260730.json`
12. `docs/btc_ml_v1/BTC_BCR13_LOCALAPPDATA_SINGLE_UPLOAD_ZIP_WORKFLOW_CORRECTION_20260730.md`
13. `docs/btc_ml_v1/BTC_BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN_CONTRACT_20260730.md`
14. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
15. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

BCR13:

- B3 machines: `0/8 capability pass`
- B3: `CLOSED_NO_CAPABILITY_SURVIVOR_NO_RESCUE`
- BCR14: `NOT_APPLICABLE_ZERO_SURVIVORS`
- B3 value fields: unopened

BCR15/BCR16:

- family: `B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM`
- frozen machines: `8`
- causal complete-H1 construction: implemented
- synthetic/exact-path tests: `6 passed`
- actual frozen 30,661-row run: pending
- B5 return/win-loss/PF/PnL/MFE/MAE: unopened
- promoted/deployable candidates: `0`

## 6. 現在の次作業

GitHub DesktopでbranchをPullし、次を実行する。

`scripts\btc_ml_v1\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\01_run_BCR16.bat`

出力先:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\LATEST`

成功後、Explorerで選択された次の1ファイルだけをアップロードする。

`99_UPLOAD_PACKAGE.zip`

失敗時は完全なconsole errorを提示する。別CSV、SHA変更、row count変更、類似ファイルfallbackは禁止。

## 7. value境界

B5 value evaluationは未承認。BCR16 packageの受領・能力監査前にreturn、win/loss、PF、PnL、MFE、MAE、portfolio、prospective start、shadowへ進まない。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

Discord、MT5発注、live-ready、final signalは未承認。

## 9. fail-closed

branch、最新版handoff、current state、next action、BCR15 contract、BCR16 readinessが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
