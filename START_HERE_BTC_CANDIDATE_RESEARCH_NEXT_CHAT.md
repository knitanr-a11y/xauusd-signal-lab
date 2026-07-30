# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_TRACK_A_AND_TRACK_B_COMPLETE_OUTCOME_BLIND_BCR08_COST_PROVENANCE_READY`
- updated: `2026-07-30T19:25:00+09:00`

## 1. branch hard gate

すべての読取りは必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branch、類似ファイルfallbackは禁止。branch取得不能または文書矛盾時は停止する。

## 2. 唯一の最新版handoff

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_TRACK_A_TRACK_B_COMPLETE_BCR08_COST_PROVENANCE_NEXT_20260730.md`

上記以外のhandoffは、ここから明示されない限り`AUDIT_HISTORY_ONLY`。

## 3. 必須read order

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_TRACK_A_TRACK_B_COMPLETE_BCR08_COST_PROVENANCE_NEXT_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_CONTRACT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr08_mt5_symbol_cost_provenance_contract_20260730.json`
8. `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`
9. `docs/btc_ml_v1/BTC_BCR05E_OUTCOME_BLIND_INTEGRATED_STATE_MACHINE_REPLAY_RESULT_20260730.md`
10. `docs/btc_ml_v1/BTC_BCR06_OUTCOME_BLIND_TRACK_B_MECHANISM_DENSITY_RESULT_20260730.md`
11. `docs/btc_ml_v1/BTC_BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINE_RESULT_20260730.md`
12. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
13. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

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

outcome-blind段階で、完全state machineを8系統まで固定した。

### Track A

- Mochipoyo source由来の完全state machine：4系統
- BCR05E package SHA: `d8fd13557f3b0a9c6d7fc9d499e7654ec4cb814f5538e41928b2e9d2c4d0ca84`
- source stateはfidelity監査専用。価値評価・shadowは必ずIDLE開始

### Track B

- B1 trend-pullback：2系統
- B4 overextension mean reversion：2系統
- B2 compression-expansion：密度不足で停止、threshold救済禁止
- BCR06 SHA: `04215689d2b861b72e737e000dfe6a6b3d2434ec2caae37b9574edd4b770027b`
- BCR07 SHA: `7b2643a00179aaa3b09c2854fa52e10e4bbad6ed9ff69d0a58e3d279ea7cb0f4`

利益、WR、PF、DD、MFE、MAEはまだ開いていない。deployable candidateは0。

## 6. 現在の次作業

`BCR08_MT5_SYMBOL_AND_COST_PROVENANCE`

利益計算前に、MT5のexact symbol、digits、point、tick size/value、contract size、spread単位、通貨、計算modeをread-onlyで取得する。

BAT：

`C:\btc-ff\scripts\btc_ml_v1\BCR08_mt5_symbol_cost_provenance\01_run_BCR08.bat`

提出ZIP：

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR08_mt5_symbol_cost_provenance\LATEST\99_UPLOAD_PACKAGE.zip`

GitHub DesktopでFetch/Pull後、既存MT5・Collector・M7Cを動かしたまま1回だけ実行する。成功・失敗を問わず最初のZIPを提出し、自動再実行しない。

## 7. runtime protection

Collector、M7C、M8C、M9、M10を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

BCR08はorder、position、order/deal history、symbol_selectを使用しない。口座番号、氏名、残高、損益を出力しない。

## 8. fail-closed

branch、最新版handoff、current state、next actionが矛盾する場合は作業停止。記憶、古いhandoff、default branch、似たファイルで補わない。
