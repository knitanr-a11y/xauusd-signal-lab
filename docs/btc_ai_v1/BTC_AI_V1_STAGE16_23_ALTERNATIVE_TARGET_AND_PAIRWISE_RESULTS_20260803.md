# BTC AI V1 Stages 16–23 — Alternative Target and Pairwise Ranking Results

Date: 2026-08-03  
Formal status: `BTC_AI_V1_CANDLE_ONLY_HISTORICAL_AI_SEARCH_EXHAUSTED_NO_SUPPORTED_CANDIDATE_NEW_PROSPECTIVE_OR_NEW_DATA_NEEDED`

## Fixed contract

- symbol: `BTCUSD#`
- MT5 broker-server time
- closed M15 decisions and exact M1 execution
- fixed spread: 22.50 USD per completed 1 BTC trade
- no fabricated M1 bars
- every count includes its calendar-month denominator
- the 2026-01 through 2026-07 seven-month period is already consumed and cannot be reused as untouched evidence

## Stages 16–20: alternative continuous targets

Three target families were frozen before outcomes:

- `NET_CLOSE_R_480`: fixed-cost directional close return after 480 exact M1 minutes, normalized by ATR
- `PATH_EDGE_R_480`: MFE minus 0.75 × MAE over 480 exact M1 minutes
- `POLICY_PAYOFF_R_720`: realized R of a fixed 1 ATR stop / 2 ATR target / 720-minute maximum-hold policy

AI models:

- XGBoost regressor
- CatBoost regressor
- ExtraTrees regressor
- Histogram Gradient Boosting regressor
- equal-weight rank ensemble

### Outcome-blind capability

- 360 raw candidates
- 359 passed explicit density/entry checks
- 120 balanced survivors
- exactly 40 survivors per target
- exactly 24 survivors per model
- LONG 60 / SHORT 60
- 272–2,619 events in 24 months = 11.33–109.13 events/month

### Development

- evaluation: 2024-01 through 2025-12, exactly 24 calendar months
- 120 candidates × 64 exits = 7,680 evaluations
- 43 configurations across six base candidates passed all development gates
- all six were LONG
- 310–667 completed trades in 24 months = 12.92–27.79 trades/month

Top development examples:

| Candidate | Target | AI | Trades/24m | Trades/month | PF | Net | DD |
|---|---|---|---:|---:|---:|---:|---:|
| `AT4_002` | NET_CLOSE_R_480 | XGBoost | 310 | 12.92 | 1.3483 | +29,030.68 | 8,462.30 |
| `AT4_038` | NET_CLOSE_R_480 | CatBoost | 342 | 14.25 | 1.2304 | +21,377.81 | 9,219.74 |
| `AT4_110` | NET_CLOSE_R_480 | rank ensemble | 335 | 13.96 | 1.2241 | +16,926.51 | 5,781.69 |
| `AT4_171` | PATH_EDGE_R_480 | ExtraTrees | 667 | 27.79 | 1.1997 | +20,867.36 | 5,503.27 |

### Robustness

- shortlist: 6
- bootstrap pass: 3/6
- matched-random pass: 6/6
- pseudo-state pass: 6/6
- parameter-neighborhood pass: 6/6
- all controls pass: 3/6
- frozen exploratory survivors: `AT4_110`, `AT4_171`, `AT4_038`

### Consumed 2026 diagnostic

The three survivors were applied to 2026-01 through 2026-07 only after freeze. This was diagnostic, not selection or support.

| Candidate | Target | AI | Trades/7m | Trades/month | PF | Net | 2026 target-score correlation |
|---|---|---|---:|---:|---:|---:|---:|
| `AT4_110` | NET_CLOSE_R_480 | rank ensemble | 52 | 7.43 | 0.6625 | -5,362.14 | -0.0262 |
| `AT4_171` | PATH_EDGE_R_480 | ExtraTrees | 136 | 19.43 | 0.7504 | -7,269.98 | +0.0196 |
| `AT4_038` | NET_CLOSE_R_480 | CatBoost | 39 | 5.57 | 0.4380 | -8,934.68 | -0.0346 |

All three lost money. No candidate was promoted or rescued.

## Stages 21–23: pairwise payoff ranking and recency adaptation

The objective was changed from absolute-value regression to direct within-month payoff ordering.

Preregistered methods:

- XGBoost `rank:pairwise`
- CatBoost `YetiRank`
- expanding training
- rolling up-to-12-month training
- the same three direct-payoff targets

### Implementation incidents

- An initial nanosecond-to-month conversion treated each row as a separate group. The affected dry-run artifact was deleted before candidate generation.
- Months with a constant `POLICY_PAYOFF_R_720` value contain no ranking pairs. A committed addendum excluded those months from ranker fitting only; they remained in calibration, validation and PnL evaluation.
- CatBoost YetiRank did not complete one month-group series within the execution limit and produced no accepted artifact. It was not replaced by a different model.

### Capability

- XGBoost model series completed: 24
- CatBoost completed artifacts: 0
- XGBoost raw candidates: 144
- explicit capability pass: 71
- survivors: 71
- expanding 35 / rolling 36
- LONG 36 / SHORT 35
- 4,649–6,482 events in 24 months = 193.71–270.08 events/month

### Development

- 71 candidates × 64 exits = 4,544 evaluations
- configurations with positive net: 0
- configurations with PF at least 1.15: 0
- development survivors: 0
- robustness and 2026 diagnostics were not opened

The highest PF was 0.9972 and remained negative. Pairwise ranking therefore failed at the basic development-value stage; no gate was relaxed.

## Formal conclusion

Across the complete BTC AI V1 candle-only research, the following were actually tested:

- deterministic causal rule search
- LightGBM and regularized logistic classification
- XGBoost, CatBoost, ExtraTrees and Histogram Gradient Boosting classification
- model-rank ensembles
- direct payoff, MFE/MAE path-edge and fixed-policy regression targets
- expanding and rolling pairwise payoff ranking

Supported candidates: **0**.

No historical untouched period remains. Continuing to multiply candle-only models on the same data would be outcome-driven overfitting. The next meaningful evidence must be genuinely new: post-2026-08 prospective candles, independent older/broker data, or separately authorized new source features such as order flow, open interest or funding.

No portfolio, Shadow, Discord, MT5 order, live-ready or final signal is authorized.
