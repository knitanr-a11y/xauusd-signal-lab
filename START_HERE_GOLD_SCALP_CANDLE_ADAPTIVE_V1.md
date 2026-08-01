# START HERE — GOLD SCALP CANDLE ADAPTIVE V1

Date: 2026-08-02  
Branch: `feature/gold-scalp-candle-adaptive-v1-research`

## Formal status

`RETROSPECTIVE_THREE_ADAPTIVE_VECTORS_COMPLETE_NO_CALIBRATION_PASS`

## User boundary

- existing GOLD candle data only;
- initial stop no greater than 5 USD;
- target no lower than 5 USD;
- breakeven allowed;
- standard spread cost is 0.30 USD once;
- target frequency is a median of at least 20 trades per month;
- target positive-PnL win rate is at least 50%.

## Completed studies

1. unsupervised preceding-30-M1 shape-state atlas;
2. post-entry 5/10/15-minute exit/hold/breakeven path manager;
3. causal online portfolio of 234 event-side-exit experts using resolved recent results.

None passed the frozen 2024H2 calibration gate. Evaluation from 2025 onward was not opened.

## Next materially distinct vector

`HIERARCHICAL_COUNTERFACTUAL_BARRIER_ROUTER`

The next study should decompose the task:

1. determine whether the future path is tradable/directional enough;
2. compare LONG and SHORT counterfactually in one model;
3. choose TP/SL/breakeven policy only after direction is chosen;
4. abstain when both sides are noisy.

This is not another direct LONG/SHORT binary classifier.

## Isolation

Frozen V19 and Challenger C1 were not used as candidate inputs and were not modified, stopped, or reconfigured.

Research only. No Shadow, Discord, MT5 order, live trading, promotion, or merge authorization.
