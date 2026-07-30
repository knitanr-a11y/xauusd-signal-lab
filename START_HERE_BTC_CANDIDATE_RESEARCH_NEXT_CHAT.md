# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR10_DIAGNOSTIC_COMPLETE_BCR11_CONTRACT_FROZEN_IMPLEMENTATION_AWAITING_AUTHORIZATION`
- updated: `2026-07-30T20:20:00+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR10_DIAGNOSTIC_COMPLETE_BCR11_FINITE_OVERLAY_NEXT_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR10_DIAGNOSTIC_COMPLETE_BCR11_FINITE_OVERLAY_NEXT_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_RESULT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr10_holding_rollover_path_diagnostic_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_CONTRACT_20260730.md`
9. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_development_contract_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR09_CORRECTED_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260730.md`
11. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_RESULT_20260730.md`
12. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
13. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
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

## 5. BCR10正式結果

- accepted package SHA: `99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0`
- six-machine episodes: `5,975`
- path complete / incomplete: `5,829 / 146`
- overlay PnL evaluated: no
- candidate selected: no

Actual-exit holding phenotype:

- all six machine aggregates with actual holding `<=16` bars: positive, PF `8.58–18.06`
- all six with actual holding `>=17` bars: negative, PF `0.08–0.15`
- rollover and holding are not equivalent: rollover `<=16` remained positive while same-day `>=17` was negative in all six machines

This is outcome-exposed description, not a validated max-hold rule.

## 6. Path finding

- path-complete final losers held `>=17`: `1,361`
- positive MFE at some point: `89.79%`
- first MFE median / q90: bar `1 / 8`
- rollover path-complete losers positive at 23:45: `8.11%`
- rollover losers with earlier positive MFE: `92.08%`

The primary next development hypothesis is finite maximum-holding control, with 23:45 flat retained as a comparator.

## 7. Current next stage

`BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_REPLAY`

The contract is frozen for exactly six overlays per six unchanged machines:

- baseline
- max hold 16 / 32 / 64 bars
- exact 23:45 server-day flat
- max hold 16 plus 23:45 flat

BCR11 implementation is not yet authorized. No BAT or upload is required now.

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 9. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
