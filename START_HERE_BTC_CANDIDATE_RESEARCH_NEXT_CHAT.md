# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_BCR11_COMPLETE_NO_CAUSAL_HOLDING_OVERLAY_ADVANCES_NEW_TRACK_B_FAMILY_NEXT`
- updated: `2026-07-30T21:46:00+09:00`
- handoff verification: `FINAL_VERIFIED_FOR_NEXT_CHAT`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR11_FINAL_VERIFIED_BCR12_AUTHORIZATION_PENDING_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_BCR11_FINAL_VERIFIED_BCR12_AUTHORIZATION_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_RESULT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_result_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_CONTRACT_20260730.md`
9. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_development_contract_20260730.json`
10. `docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_RESULT_20260730.md`
11. `configs/btc_ml_v1/btc_bcr10_holding_rollover_path_diagnostic_result_20260730.json`
12. `docs/btc_ml_v1/BTC_BCR09_CORRECTED_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260730.md`
13. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_RESULT_20260730.md`
14. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
15. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
16. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
17. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

2026-07-30 correction: BCR11 contract JSONとBCR10 result JSONを、frozen handoff policyと一致する正式read orderへ復元した。BCR11の結果・decision・status、およびBCR12の承認境界に変更はない。

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

## 5. BCR11正式結果

- accepted package SHA: `6e10e296e57f2ba9359f29e83711acd9069944f31f9cca78ec65d6587c1299d8`
- six machines × six overlays: `36` trials
- baseline episode parity: all six exact
- non-baseline C0 positive / PF>=1: `0 / 0`
- non-baseline C2 positive / PF>=1: `0 / 0`
- overlay proposal advanced: `0`
- deployable candidate: `0`
- prospective start / shadow: none

Best C0 and C2 rows remained unchanged B4 E0 baseline:

- C0 PF `1.000623`, net `+108.97 USD / 1 lot`
- C2 PF `0.949662`, net `-8,951.03 USD / 1 lot`

## 6. Interpretation boundary

BCR10の「実際に16本以内で終わった群」は未来のbase exit時間で分類された記述群だった。

16本強制決済ではstateが早くIDLEへ戻り、後続entryが増えてepisode列全体が変わる。max hold 16ではbase episodeの`24.25%〜38.02%`が変化し、各machineで`108〜553`件の新規entryが発生した。全6系統でC0/C2とも負のままだった。

23:45 flatもrolloverを除去したが、正の価値を作らなかった。

したがって現行Track A/B4の負け削減overlay救済は終了する。B1はreject、B2はblockedを維持し、threshold救済をしない。

## 7. 現在の次作業

推奨候補：

`BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN`

ただし、BCR12は未承認。新チャットを開始したこと自体を承認とみなさない。

次はparameter救済ではなく、breakout/retest/re-acceleration、causal HTF regime + M15 execution、方向非対称mechanism等の、経済原理が異なる新familyをoutcome-blindで契約する。

現在、BAT・追加ファイル・prospective start・shadowは不要。必要read order完了後、正式状態と承認境界を報告してユーザーの明示指示を待つ。

## 8. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 9. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
