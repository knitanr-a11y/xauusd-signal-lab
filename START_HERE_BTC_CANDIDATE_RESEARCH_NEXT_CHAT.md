# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR13_COMPLETE_ZERO_OF_EIGHT_B3_MACHINES_PASS_CAPABILITY_BCR14_NOT_APPLICABLE_BCR15_AUTHORIZATION_PENDING`
- updated: `2026-07-30T23:26:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR13_COMPLETE_ZERO_OF_EIGHT_PASS_BCR15_AUTHORIZATION_PENDING_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR13_COMPLETE_ZERO_OF_EIGHT_PASS_BCR15_AUTHORIZATION_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_RESULT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr13_b3_outcome_blind_density_and_state_machine_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR13_LOCALAPPDATA_SINGLE_UPLOAD_ZIP_WORKFLOW_CORRECTION_20260730.md`
9. `configs/btc_ml_v1/btc_bcr13_localappdata_single_upload_zip_workflow_correction_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_IMPLEMENTATION_READY_20260730.md`
11. `configs/btc_ml_v1/btc_bcr13_b3_outcome_blind_density_implementation_ready_20260730.json`
12. `docs/btc_ml_v1/BTC_BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN_CONTRACT_20260730.md`
13. `configs/btc_ml_v1/btc_bcr12_materially_new_outcome_blind_track_b_mechanism_design_contract_20260730.json`
14. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_RESULT_20260730.md`
15. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_result_20260730.json`
16. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_CONTRACT_20260730.md`
17. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_development_contract_20260730.json`
18. `docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_RESULT_20260730.md`
19. `configs/btc_ml_v1/btc_bcr10_holding_rollover_path_diagnostic_result_20260730.json`
20. `docs/btc_ml_v1/BTC_BCR09_CORRECTED_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260730.md`
21. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_RESULT_20260730.md`
22. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
23. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
24. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
25. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

## 5. BCR13正式結果

- family: `B3_BREAKOUT_RETEST_REACCELERATION`
- frozen machines: `8`
- accepted inner package SHA256: `cc1483c0e8b538eb32b67dce0a10df8733c5e7f5f924c9080f945ebddc72e51d`
- deterministic repeat: exact match
- frozen input: `30,661` rows, SHA256 `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- capability pass / fail: `0 / 8`
- B3 outcome fields opened: no
- promoted/deployable candidate: `0`

全8 machinesが同じ5基準で不合格。

1. closed episodeが50未満
2. 各方向closed episodeが20未満
3. entry monthが6未満
4. 最大月集中が35%超
5. p90 holdingが384本超

entriesは`5〜8`、closed episodesは`4〜7`、entry monthは全machineで`2`。全machineがendpoint-open SHORTを1件持ち、position occupancyは`97.86%〜97.99%`だった。

state integrityは全machineでtrue。fallback、補間、simultaneous conflict、gap cancel、exact-entry-missingはない。

## 6. B3 familyとBCR14

B3は次で閉じる。

`CLOSED_NO_CAPABILITY_SURVIVOR_NO_RESCUE`

threshold緩和、side削除、exit救済、9個目のmachine、追加gridは禁止。

BCR14はBCR13 capability survivorだけを対象にしたvalue gateとして予約されていた。survivorが0のため、次で固定する。

`BCR14_NOT_APPLICABLE_ZERO_SURVIVORS`

B3 return、win/loss、PF、PnL、MFE、MAEを開かない。

## 7. 現在の次作業

推奨次stage:

`BCR15_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN`

ただしBCR15は未承認。今回のZIP提出や新チャット開始を承認とみなさない。

明示承認前はBCR15 contract、formula、threshold、implementation、test、BAT、historical resultを作らない。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

Discord、MT5発注、prospective start、shadow、live-ready、final signalは未承認。

## 9. fail-closed

branch、最新版handoff、current state、next action、BCR13 resultが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
