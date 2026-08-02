# GOLD SCALP FIRST-PASSAGE V1 — Consolidated Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_FIRST_PASSAGE_FOUR_VECTOR_COMPLETE_NO_FORMAL_CANDIDATE`**

## Contract

The study used only the existing GOLD candle data.

- MT5 broker-server naive time;
- exact M1 outcome resolution;
- spread 0.30 USD once;
- initial SL no greater than 5 USD;
- TP no lower than 5 USD;
- breakeven movement allowed;
- structural event fixes the trade direction;
- protective-stop-first handling when adverse and favorable barriers are both reachable in one M1;
- one-position non-overlap.

The pseudo-forward target blocks were 2024H1, 2024H2, 2025H1, 2025H2, 2026H1 and 2026JUL. For each target block, older data was used for model estimation and the immediately preceding block for calibration.

## Joint first-passage labels

A total of 170,664 structural candidate rows were measured against favorable barriers of +5, +7.5 and +10 USD and adverse barriers of -2.5, -3.5 and -5 USD.

The hierarchical path classes were:

- ambiguous: 44,468;
- clean TP5: 9,109;
- clean TP7.5: 7,300;
- clean TP10: 30,494;
- adverse-fast: 79,293.

The large adverse-fast class showed that many structural event onsets moved against their declared side before producing a clean favorable passage.

## Vector A — global LightGBM first-passage router

The model predicted five path classes rather than a direct win/loss label. It used causal M5, H1 and H4 context, event identity, regime, side and event quality. A predicted clean path selected TP5, TP7.5 or TP10, while the adverse-fast probability acted as an abstention margin.

Three exit profiles were tested:

- fixed;
- defensive;
- breakeven.

No configuration passed the frozen calibration gate in any of the six target blocks.

The first implementation exceeded the compute budget because every configuration repeatedly rebuilt and sorted pandas trade ledgers. A compute-only amendment replaced that operation with a chronological one-position selector. Features, labels, model parameters, thresholds, margins, blocks and gates were preserved. The fast rerun still produced zero calibration passes.

## Vector B — empirical first-passage distributions

A model-free comparison estimated smoothed path distributions in historical cells defined by event, regime, structural side and historical event-quality tercile. Event-side fallback distributions were used for previously unseen cells.

No configuration passed the calibration gate in any of the six target blocks. The empirical clean-class posterior was generally too diffuse to produce both useful frequency and the required historical quality.

## Vector C — event-specific first-passage specialists

The global model could have hidden different behavior across structural families, so six independent specialists were trained:

1. M5 gap fill;
2. compression release;
3. effort/result continuation;
4. false-break fade;
5. HTF pullback resume;
6. volume absorption.

Two component gates were tested. Each passing event specialist was frozen from the calibration block and applied to the next block. Simultaneous and overlapping target trades were removed globally.

### BALANCED aggregate

- trades: 170;
- positive-PnL win rate: 34.71%;
- PF: 1.0539;
- net: +25.68 USD;
- DD: 76.00 USD;
- median monthly trades: 5;
- positive months: 12 / 31.

Target-block results:

| Block | n | WR | PF | Net |
|---|---:|---:|---:|---:|
| 2024H1 | 26 | 19.23% | 0.3767 | -63.58 |
| 2024H2 | 25 | 44.00% | 1.5609 | +38.14 |
| 2025H1 | 38 | 36.84% | 1.1189 | +11.47 |
| 2025H2 | 81 | 35.80% | 1.1885 | +39.65 |
| 2026H1 | 0 | — | — | 0.00 |
| 2026JUL | 0 | — | — | 0.00 |

Event contributions in the BALANCED aggregate:

- M5 gap fill: 66 trades, +38.65 USD;
- HTF pullback resume: 25 trades, +38.14 USD;
- compression release: 38 trades, +11.47 USD;
- volume absorption: 41 trades, -62.58 USD.

Volume absorption illustrates the calibration-forward problem. It passed historical component gates but reversed sharply in the next block.

### STRICT aggregate

- trades: 54;
- win rate: 25.93%;
- PF: 0.6480;
- net: -68.41 USD;
- DD: 115.33 USD.

Increasing the historical component standard did not improve forward quality.

## Vector D — favorable/adverse arrival-time hazard router

The final model-free vector did not classify path classes. For each historical event cell and candidate exit it estimated:

- robust mean realized PnL;
- historical positive-PnL rate;
- median time to the favorable barrier;
- median time to the adverse barrier;
- favorable/adverse median-time ratio.

Only one target block was opened by the frozen calibration gate.

### 2025H1 calibration

- n: 64;
- win rate: 51.56%;
- PF: 1.8419;
- net: +112.12 USD;
- median: 9.5 trades/month;
- positive months: 5 / 6.

### Frozen 2025H2 target

- n: 97;
- win rate: 34.02%;
- PF: 0.9179;
- net: -19.56 USD;
- DD: 44.61 USD;
- median: 16.5 trades/month;
- positive months: 3 / 6.

The arrival-time relationship changed materially between adjacent half-years. A strong favorable/adverse speed separation in the calibration block did not remain favorable in the target block.

## Candidate observation catalog

Three target-block-positive components are retained for descriptive observation only:

- HTF pullback resume in 2024H2;
- M5 gap fill in 2025H2;
- compression release in 2025H1.

They are not validated candidates because each is supported by only one positive target block, their win rates are below the requested 50% threshold, and repeated multi-block confirmation is absent.

## Formal conclusion

`NO_FORMAL_CANDIDATE`

Joint first-passage information improved the description of exits and sometimes found profitable single blocks, but it did not solve directional instability across changing market environments.

Do not restore positive single blocks as candidates, interpolate thresholds, delete losing blocks, or add post-result hour, month, direction or volatility filters.

## Next materially distinct boundary

The next candle-only research should stop treating each candidate onset as an isolated point. A distinct hypothesis is a causal **event-sequence grammar** using ordered state transitions and dwell times, for example:

`compression -> sweep -> reclaim -> effort/result expansion`

or

`HTF pullback -> failed continuation -> opposite reclaim`

The sequence must be defined before outcomes, with one eligible entry per completed grammar. Independently preregistered grammar engines can then be added to the candidate catalog and accumulated across different structural causes.

No Shadow, Discord, MT5 order, live trading, promotion or merge authorization follows from this audit. Frozen V19 and Challenger C1 were not modified, stopped, reconfigured or used as candidate inputs.