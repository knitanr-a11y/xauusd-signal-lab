# BTC AI V1 — Research History Index

Chronological authority for `BTC_AI_CANDIDATE_RESEARCH_V1`.

## 2026-08-03 — Stage 00 / 00A: XM source acquisition, audit and cost freeze

- `docs/btc_ai_v1/BTC_AI_MT5_HISTORY_EXPORTER_20260803.md`
- `docs/btc_ai_v1/BTC_AI_V1_SOURCE_ACCEPTANCE_AND_FIXED_COST_CONTRACT_20260803.md`
- `config/btc_ai_v1/source_data_manifest_20260803.json`
- `config/btc_ai_v1/fixed_cost_contract_20260803.json`
- BTCUSD# M1/M5/M15/H1/H4/D1 accepted and hash-frozen.
- no GOLD contamination; exact M1 reconstruction parity passed.
- fixed spread frozen at 22.50 USD per completed 1 BTC trade.

## Stage 01: XM research-design preregistration

- `config/btc_ai_v1/research_design_contract_20260803.json`
- four expanding validation folds covering 24 development months, 2024-01 through 2025-12.
- untouched final frozen as 2026-01 through 2026-07, seven months.
- exact-M1 execution, no-rescue, robustness and frequency contracts frozen.

## Stages 02–04: deterministic causal-rule cycle

- 1,200 raw candidates; 300 outcome-blind survivors.
- 19,200 execution evaluations over 24 months.
- nine development base survivors; zero passed all robustness controls.
- classification: `PROMISING_NOT_ROBUST_NO_FINALIST`.

## Stages 05–10: binary supervised-ML cycle

- LightGBM and regularized logistic regression.
- 144 definitions; 72 capability survivors; 4,608 execution evaluations over 24 months.
- 11 development survivors; nine robustness passes; five finalists.
- untouched 2026 seven-month result: all five lost; supported candidates 0.
- the 2026 period became consumed.

## Stage 11: regime and discrimination forensic

- `docs/btc_ai_v1/BTC_AI_V1_STAGE11_REGIME_SHIFT_FORENSIC_20260803.md`
- 2026 SHORT base-label rate remained 36.53%, but finalist AUC fell to approximately 0.508–0.523.
- daily-trend state inverted.
- conclusion: `REGIME_AND_CONDITIONAL_RELATIONSHIP_SHIFT_MODEL_DISCRIMINATION_COLLAPSE`.

## Stages 12–15: diverse classifier AI

- XGBoost, CatBoost, ExtraTrees, Histogram Gradient Boosting and rank ensemble.
- 120 raw; 60 outcome-blind survivors over 24 months.
- four development survivors; two passed robustness.
- both lost in the consumed seven-month 2026 diagnosis.
- supported candidates remained 0.

## Stages 16–20: alternative continuous-target AI

- direct close payoff, MFE/MAE path edge and fixed-policy payoff targets.
- XGBoost, CatBoost, ExtraTrees and Histogram Gradient Boosting regressors plus rank ensemble.
- 360 raw; 120 balanced survivors; 7,680 execution evaluations over 24 months.
- six development survivors; three passed robustness.
- all three lost in the consumed 2026 diagnosis.
- supported candidates remained 0.

## Stages 21–23: pairwise payoff ranking

- XGBoost `rank:pairwise`, expanding and rolling-12-month schedules.
- CatBoost YetiRank produced no accepted artifact and was not replaced.
- 144 raw; 71 capability survivors; 4,544 execution evaluations over 24 months.
- positive-net configurations: 0; development survivors: 0.

## Stage 24A: immediate Binance USD-M futures acquisition

User rejected waiting several months for new prospective data. Research immediately switched to available independent history.

- acquisition script: `scripts/btc_ai_v1/download_binance_external_validation.py`
- workflow: `.github/workflows/btc_ai_v1_external_validation.yml`
- GitHub Actions run: `30786496193`
- official `BTCUSDT` USD-M perpetual monthly data, 2020-01 through 2022-12.
- 36 calendar months; 1,578,240 M1 rows.
- calendar-minute coverage 100%; duplicates, reversals and gaps all 0.
- all 36 monthly funding archives available.
- all source ZIPs verified against published checksums.

Contract:

- `config/btc_ai_v1/binance_external_validation_contract_20260803.json`
- fit 2020, calibration 2021H1, development 2021H2, untouched final 2022.
- 48 frozen AI candidates using candle context versus volume/trade-count/taker-buy/funding features.

Development over six calendar months:

- four development survivors.
- two robustness survivors.

Untouched 2022 over twelve months:

- `BEX_CANDLE_CONTEXT_SHORT_XGBR_P95`: 260 trades / 12 months = 21.67/month; PF 0.9850; net -536.84; positive months 4/12; FAIL.
- `BEX_MICRO_FUNDING_SHORT_XGB_P95`: 94 / 12 = 7.83/month; PF 1.1106; net +1,409.85; positive months 4/12; FAIL versus frozen 7/12 requirement.

Result:

- `docs/btc_ai_v1/BTC_AI_V1_BINANCE_FUTURES_EXTERNAL_VALIDATION_RESULT_20260803.md`
- supported candidates: 0.
- no gate relaxation or rescue.

Implementation incident:

- first dry run mixed M15 candidate-row and M1 resolution-row units in the non-overlap gate.
- the dry run was rejected; accepted rerun compared exact M1 entry and resolution indices.

## Stage 24B: immediate Binance spot acquisition and validation

- acquisition script: `scripts/btc_ai_v1/download_binance_spot_external_validation.py`
- workflow: `.github/workflows/btc_ai_v1_binance_spot_external_validation.yml`
- GitHub Actions run: `30787147478`
- official `BTCUSDT` spot monthly data, 2018-01 through 2019-12.
- 24 calendar months; 1,045,460 M1 rows.
- duplicates and reversals 0.
- 16 exchange-gap intervals were retained as gaps and never interpolated.
- exact usable M15 decisions: 68,875.
- all source ZIPs verified against published checksums.

Contract:

- `config/btc_ai_v1/binance_spot_external_validation_contract_20260803.json`
- fit 2018H1, calibration 2018H2, development 2019H1, untouched final 2019H2.
- 48 frozen AI candidates using candle context versus volume/trade-count/taker-buy features.

Development over six calendar months:

- all 48 candidates failed.
- best PF: 0.7112 with negative net.
- robustness and 2019H2 final were not opened.

Result:

- `docs/btc_ai_v1/BTC_AI_V1_BINANCE_SPOT_EXTERNAL_VALIDATION_RESULT_20260803.md`
- supported candidates: 0.

## Immediate external-evidence total

- independent history added without waiting: 60 calendar months.
- independent M1 rows: 2,623,700.
- venues/tracks kept separate: Binance spot and Binance USD-M perpetual.
- combined result: `config/btc_ai_v1/external_validation_result_20260803.json`.
- supported candidates: **0**.

## Current next stage

`BTC_AI_V1_25_DERIVATIVES_METRICS_MARK_PREMIUM_OPEN_INTEREST_RESEARCH`

Latest handoff:

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_EXTERNAL_5Y_DONE_DERIVATIVES_METRICS_NEXT_20260803.md`

Continue immediately with official mark-price, premium-index, open-interest, funding and long-short-ratio evidence from Binance, Bybit and Deribit. Compare incremental value against the frozen candle/volume baseline. Keep venue execution ledgers separate and do not rescue any rejected candidate.

No portfolio, Shadow, Discord, MT5 order, live-ready or final signal is authorized.
