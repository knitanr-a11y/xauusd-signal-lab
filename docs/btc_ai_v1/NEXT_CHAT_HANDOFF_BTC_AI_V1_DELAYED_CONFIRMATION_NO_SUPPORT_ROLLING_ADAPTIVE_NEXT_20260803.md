# NEXT CHAT HANDOFF — BTC AI V1 delayed confirmation complete, no support, rolling adaptation next

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_OHLC_STATIC_AND_DELAYED_CONFIRMATION_NO_DIRECTIONAL_SURVIVOR`

## Authority

Use only the accepted XM `BTCUSD#` closed-bar OHLC snapshot.

- M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- fixed spread remains 22.50 USD for later candidate PnL
- no external or volume features
- Stage 29/30 did not open candidate PnL or 2026

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
3. `docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_MASTER_PACKAGE_V3_MANIFEST_20260803.md`
4. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
5. `config/btc_ai_v1/ohlc_anchor_age_path_shape_conditional_model_contract_20260803.json`
6. all Stage 29 addenda
7. `docs/btc_ai_v1/BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_RESULT_20260803.md`
8. `config/btc_ai_v1/ohlc_anchor_age_path_shape_result_20260803.json`
9. `config/btc_ai_v1/ohlc_delayed_confirmation_state_machine_forensic_contract_20260803.json`
10. `docs/btc_ai_v1/BTC_AI_V1_OHLC_DELAYED_CONFIRMATION_STATE_MACHINE_RESULT_20260803.md`
11. `config/btc_ai_v1/ohlc_delayed_confirmation_state_machine_result_20260803.json`
12. `config/btc_ai_v1/current_state_20260803.json`
13. `config/btc_ai_v1/next_action_20260803.json`
14. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

## Stage 29 — anchor-age/path-shape

- anchors 2023–2025: 42,018
- generated anchor-age rows: 672,257
- formal 2024–2025 rows: 461,483 over 24 months
- ordinary baseline: 112,784 directed rows
- all six families and fifteen subtypes retained

Magnitude:

- MFE delta Spearman -0.0022; error worsened 1.54%
- MAE delta +0.0004; error worsened 1.09%
- four-bar range delta +0.0032; error worsened 2.18%
- magnitude support survivors 0

Direction:

- cross-fitted residual Spearman 0.0541
- P90 rows 43,056 / 24 months = 1,794/month
- monthly min/median/max 1,025 / 1,755.5 / 2,602
- actual residual mean +0.0411 versus required +0.08
- D1 DOWN actual residual -0.0042
- direction support survivors 0

Feature gain:

- current OHLC 79.26%
- path core 19.40%
- family identity 0.71%
- subtype identity 0.64%

Accepted rerun only:

- zero-origin MFE/MAE
- LightGBM bagging frequency 1
- all initial noncompliant dry runs invalidated

Formal result:

`ANCHOR_AGE_PATH_SHAPE_ADDS_SMALL_UNSTABLE_DIRECTIONAL_RESIDUAL_AND_DOES_NOT_IMPROVE_MAGNITUDE_BASELINE`

## Stage 30 — delayed confirmation

First confirmation events over 24 months:

- total 95,440
- actionable 70,892
- diagnostic 24,548

Actionable results:

| State | Events / 24m | Per month | Oriented residual |
|---|---:|---:|---:|
| failed acceptance/reclaim reversal | 16,111 | 671.29 | -0.0161 |
| deep pullback reversal | 17,417 | 725.71 | -0.0103 |
| mature extension reversal | 8,164 | 340.17 | +0.0081 |
| shallow pullback continuation | 8,528 | 355.33 | -0.0107 |
| accepted continuation | 9,596 | 399.83 | -0.0266 |
| adverse-dominant reversal | 11,076 | 461.50 | +0.0031 |

All six states failed the frozen +0.08 effect gate and failed time/D1 invariance. Support survivors 0.

Formal result:

`SIMPLE_DELAYED_CONFIRMATION_STATES_DO_NOT_CREATE_DIRECTIONAL_EDGE_BEYOND_CURRENT_OHLC_BASELINE`

## Cumulative packages

Latest cumulative package:

- `BTC_AI_V1_MASTER_RESEARCH_PACKAGE_20260803_V3.zip`
- SHA256 `4a5d498cada1131bf84eb855016026fb889fdcbaad58cd840669fd04c3dfa53b`
- 689 files; approximately 270 MB; expansion-tested
- includes all formal work Stage 00–30, original archives and extracted contents
- no raw candles, GOLD or external data

## Formal current conclusion

The problem is not solved by:

- more static OHLC features;
- broad model diversity;
- sequence GRU;
- anchor identity;
- anchor age/path shape;
- simple delayed ATR confirmations.

The relation between OHLC and future directional payoff remains time- and D1-dependent. Formal supported candidates remain **0**.

## Next stage

`BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_FORENSIC_PREREGISTRATION`

Target the drift mechanism directly:

1. same frozen OHLC feature/label universe;
2. monthly refit and calibration;
3. compare expanding versus rolling 3-, 6- and 12-month training windows;
4. outcome-blind minimum training support;
5. report next-month AUC, top-tail label lift and calibration by month, half-year and D1;
6. no PnL until a schedule improves ordering consistently;
7. 2026 remains diagnostic-only after schedule freeze.

## Hard boundaries

- no external or volume data
- no use of 2026 for schedule/window/model/threshold selection
- no post-result D1 filter
- no rescue of Stage 29 ages/families or Stage 30 states
- no gate reduction
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal
- do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO
