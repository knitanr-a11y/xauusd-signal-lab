# GOLD SCALP CANDLE ADAPTIVE V1 — Interim Research Audit

Date: 2026-08-02

Formal status: `RETROSPECTIVE_THREE_ADAPTIVE_VECTORS_COMPLETE_NO_CALIBRATION_PASS`

## User boundary

- Existing candle data only.
- Initial stop no greater than 5 USD.
- Target no lower than 5 USD.
- Breakeven allowed.
- Standard spread cost is 0.30 USD once.
- Evaluation from 2025 onward remains unopened unless the fixed 2024H2 calibration gate passes.

Calibration gate:

- at least 120 selected trades;
- median at least 20 trades/month;
- positive-PnL win rate at least 50%;
- PF at least 1.20;
- at least four positive months out of six.

## Study A — Unsupervised M1 shape-state atlas

The preceding 30 M1 bars were represented by eight raw-sequence channels plus causal higher-timeframe and clock context. StandardScaler, IncrementalPCA(24), and MiniBatchKMeans with 64, 128, and 256 states were fit on data before 2024-07-01 only.

Each cluster and side selected one of nine exit policies using TRAIN only. Four fixed cell-acceptance ladders were tested.

No calibration row passed.

The closest row was:

- 64 states;
- positive-LCB cells;
- 602 trades;
- median 104 trades/month;
- win rate 38.54%;
- PF 0.9886;
- net -18.73 USD;
- three of six positive months.

2025+ evaluation was not opened.

## Study B — Post-entry path manager

Two base policies were tested:

- TP5 / SL3 / 120 minutes;
- TP7.5 / SL3.5 / 180 minutes.

At 5, 10, or 15 minutes, side/base/checkpoint-specific regularized LightGBM regressors compared:

- exit at the next exact M1 open;
- hold the base policy;
- move the stop to breakeven and hold.

Features included current signed PnL, MFE, MAE, path efficiency, recent signed momentum, post-entry range/volume/spread, the pre-entry 30-M1 representation, and causal higher-timeframe context.

No calibration row passed. The best PF was approximately 0.833, with win rates below 35%.

2025+ evaluation was not opened.

## Study C — Online adaptive expert portfolio

A total of 234 experts were maintained:

- 13 event families;
- LONG and SHORT;
- nine exit policies.

All hypothetical expert signals were tracked. At each decision only records whose exit had already resolved were eligible. Fixed 60, 120, and 180-day variants used shrunk recent mean PnL, standard-error penalties, optional PF gating, and an optional two-event consensus.

No calibration row passed.

The closest row was:

- 60-day lookback;
- minimum 30 resolved observations;
- one-standard-error penalty;
- 1,028 trades;
- median 164.5 trades/month;
- win rate 34.44%;
- PF 0.9580;
- net -106.01 USD;
- three of six positive months.

2025+ evaluation was not opened.

## Interpretation

The failures are informative:

1. unsupervised market-state segmentation did not isolate a profitable high-frequency subset;
2. post-entry management could not repair weak entries;
3. recent realized performance of rule experts was not persistent enough for online switching.

The next materially different candle-only study should decompose the decision rather than predict a trade directly:

- Stage 1: predict whether the next path is sufficiently directional/tradable;
- Stage 2: compare LONG and SHORT counterfactually in one model;
- Stage 3: choose an exit policy only after direction and tradability are established;
- allow abstention when LONG and SHORT are both noisy.

This is a hierarchical counterfactual barrier router, not another direct binary entry model.

## Authorization

Research only. No Shadow, Discord, MT5 order, live trading, promotion, or merge.
