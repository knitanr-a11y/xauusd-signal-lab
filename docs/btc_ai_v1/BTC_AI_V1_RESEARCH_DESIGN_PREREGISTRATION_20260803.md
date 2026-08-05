# BTC AI V1 — Research Design Preregistration

Date: 2026-08-03  
Status: `FROZEN_BEFORE_CANDIDATE_OUTCOME_INSPECTION`

## Purpose

Discover new BTCUSD# candidates from the accepted 2023–2026 source snapshot using AI-assisted hypothesis generation and deterministic causal replay.

AI is used as a research assistant for proposing hypotheses, combining features, implementing tests and auditing results. It is not an opaque runtime decision-maker. Every candidate must be expressible as a fixed reproducible rule/configuration.

No GOLD candidate logic and no old BTC BCR candidate is imported. Only research-process safeguards are retained: closed bars, exact M1 replay, no fallback, stop-first ambiguity handling, preregistration, no post-result rescue, and robustness controls.

## Time and data roles

- MT5 broker-server naive time only.
- M15 is the primary decision grid.
- A signal M15 bar is decided at its close (`open time + 15 minutes`).
- Entry is the exact M1 open at that decision time.
- M1 is execution-only.
- M5/M15/H1/H4/D1 may provide causal features only when fully closed by decision time.
- Missing exact entry M1 suppresses the event.
- Future-confirmed pivots or ZigZag are prohibited.

## Expanding development folds

| Fold | Fit | Validation |
|---|---|---|
| 1 | 2023-01-01–2023-12-31 | 2024H1 |
| 2 | 2023-01-01–2024H1 | 2024H2 |
| 3 | 2023-01-01–2024 | 2025H1 |
| 4 | 2023-01-01–2025H1 | 2025H2 |

Untouched final test:

`2026-01-01 00:00 <= decision_time < 2026-08-01 00:00`

The partial August 2026 source tail is quarantined and not used.

The final-test outcomes must remain unopened until candidate definitions, parameters, development rankings and the maximum-five finalist list are frozen.

## Candidate families

1. trend continuation / pullback / reclaim;
2. breakout / compression / expansion;
3. mean reversion / exhaustion;
4. multi-timeframe alignment or disagreement;
5. volatility state and transition;
6. candle / swing / episode state.

Allowed features are causal normalized returns, ATR, candle geometry, EMA state, RSI/MACD, past-only rolling highs/lows and swings, volume ratios, server time, and cross-timeframe states.

No absolute price-level optimization, external economic labels, final-test-derived features, or old candidate seeding is allowed.

## Search budget

- maximum raw candidates: 1,200;
- maximum per family: 200;
- outcome-blind capability survivors: maximum 300;
- development shortlist: maximum 20;
- untouched-final finalists: maximum 5.

All candidate IDs, parameters, event ledgers and results must be retained. Outcome-blind density and diversity checks may not use PnL.

## Execution grid

Frozen combinations:

- M15 ATR14 stop: 0.50, 0.75, 1.00 or 1.50 ATR;
- target: 1.0R, 1.5R, 2.0R or 3.0R;
- maximum holding: 240, 480, 720 or 1,440 exact M1 minutes;
- spread: fixed 22.50 USD once per completed one-lot trade;
- one non-overlapping position per candidate;
- no partial, runner, trailing stop or second entry;
- same M1 TP/SL collision: SL first;
- missing M1 before resolution: INVALID, excluded and logged.

LONG, SHORT or paired direction must be defined before value results. A losing side cannot be deleted afterward.

## Development gates

A candidate can enter the development shortlist only when all apply:

- at least 120 validation trades total;
- at least 20 in each validation fold;
- aggregate validation PF at least 1.15 after fixed cost;
- aggregate validation net positive;
- PF above 1 and positive net in at least three of four validation folds;
- worst validation PF at least 0.80;
- net / maximum drawdown at least 0.25;
- no single month supplies more than 50% of gross profit.

## Robustness controls

For shortlist candidates:

- 2,000 month-block bootstrap iterations;
- bootstrap probability of positive net at least 0.95;
- bootstrap fifth-percentile PF at least 0.95;
- 2,000 matched-random controls preserving month, direction and count;
- actual net and PF at or above the 95th percentile;
- 2,000 pseudo-state controls;
- parameter-neighborhood stability;
- +1 and +5 minute entry-delay diagnostics;
- Holm adjustment across finalists, adjusted one-sided p no greater than 0.10.

## Untouched-final gates

After the finalist registry is frozen, the 2026 final test is opened once.

Required:

- at least 40 trades;
- PF at least 1.10;
- positive net;
- net / maximum drawdown at least 0.25;
- PF degradation versus development no greater than 0.25 absolute;
- no single month supplies more than 70% of gross profit;
- invalid exact-M1 rate no greater than 1%.

## Classification

- `SUPPORTED_RETROSPECTIVE`: all formal gates pass;
- `PROMISING_NOT_ROBUST`: some positive evidence, but at least one gate fails;
- `REJECT`: insufficient positive evidence.

No retrospective classification authorizes Shadow, Discord, live-ready, final signal or MT5 order execution. Prospective Shadow requires a separate contract and explicit user authorization.

## No-rescue rule

After validation or final results, do not alter thresholds, direction, sessions, months, exits, horizons or the fixed cost. A modified candidate is a new research cycle and may not reuse the opened final test as untouched evidence.
