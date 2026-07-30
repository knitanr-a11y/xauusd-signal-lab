# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR12_B3_BREAKOUT_RETEST_REACCELERATION_CONTRACT_FROZEN_BCR13_AUTHORIZATION_PENDING`
- updated: `2026-07-30T21:57:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR12_B3_CONTRACT_FROZEN_BCR13_AUTHORIZATION_PENDING_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR12_B3_CONTRACT_FROZEN_BCR13_AUTHORIZATION_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN_CONTRACT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr12_materially_new_outcome_blind_track_b_mechanism_design_contract_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_RESULT_20260730.md`
9. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_result_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_CONTRACT_20260730.md`
11. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_development_contract_20260730.json`
12. `docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_RESULT_20260730.md`
13. `configs/btc_ml_v1/btc_bcr10_holding_rollover_path_diagnostic_result_20260730.json`
14. `docs/btc_ml_v1/BTC_BCR09_CORRECTED_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260730.md`
15. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_RESULT_20260730.md`
16. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
17. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
18. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
19. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

## 5. BCR12正式到達点

- family: `B3_BREAKOUT_RETEST_REACCELERATION`
- mechanism: structural breakout → retest → closed-bar re-acceleration
- frozen machines: `8`
- lookback `L`: `32 / 64`
- breakout displacement `D`: `0.25 / 0.50 ATR`
- first-retest deadline `W`: `4 / 8 M15 bars`
- B3 outcome opened: no
- implementation/BAT: none
- promoted/deployable candidate: `0`

B3は完全確定済みM15バーだけを使う。current bar high/low/close、未来結果、fallback、補間、H1/H4/D1、source stateは使用しない。

## 6. BCR11正式結果は変更なし

- accepted package SHA: `6e10e296e57f2ba9359f29e83711acd9069944f31f9cca78ec65d6587c1299d8`
- six machines × six overlays: `36` trials
- baseline episode parity: all six exact
- non-baseline C0 positive / PF>=1: `0 / 0`
- non-baseline C2 positive / PF>=1: `0 / 0`
- overlay proposal advanced: `0`
- deployable candidate: `0`
- prospective start / shadow: none

Track A/B4のactive rescueは終了。B1はreject、B2はblockedを維持し、threshold救済をしない。

## 7. 現在の次作業

推奨候補：

`BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`

ただしBCR13は未承認。

BCR13で許可され得るのは、凍結済み8 machinesの実装と、PnLを含まない件数・方向・月・holding・occupancy・gap・state integrityの監査だけ。return、win/loss、PF、PnL、MFE、MAE、future exit resultは開かない。

新チャット開始やBCR12契約完了をBCR13承認とみなさない。明示指示を待つ。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

Discord、MT5発注、prospective start、shadow、live-ready、final signalは未承認。

## 9. fail-closed

branch、最新版handoff、current state、next action、BCR12契約が矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
