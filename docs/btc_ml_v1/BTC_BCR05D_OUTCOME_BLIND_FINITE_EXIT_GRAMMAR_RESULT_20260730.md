# BTC BCR05D — outcome-blind finite exit grammar result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T18:30:00+09:00`
- status: `READY_OUTCOME_BLIND_FINITE_EXIT_GRAMMAR_FIDELITY_RESULT`
- profitability outcomes: not opened
- final exit formula: not selected

## 1. Frozen grammar

BCR05D evaluated exactly 16 LONG-exit and 16 SHORT-exit grammars.

The axes were frozen before evaluation:

- absolute RCI9 threshold: `40`, `60`, `70`, `80`;
- optional direction-consistent EMA-slope gate;
- optional direction-consistent extension gate.

No continuous threshold search, ATR gate, compression gate, clock gate, event-distance predicate or state-age predicate was added.

Inputs:

- BCR04 SHA256: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- BCR05C SHA256: `221280603569054f3ffc23c6698446e377f9d650d288fa3d08d224a8e3925af3`
- contract commit: `8d43cc4b91c94e97ba097fd6e7b69fc51e990603`

## 2. Evaluation populations

- LONG source exits: `17`
- compatible ACTIVE_LONG controls: `223`
- SHORT source exits: `10`
- compatible ACTIVE_SHORT controls: `168`

Every grammar retained the same event and control denominators.

## 3. Advanced LONG-exit variants

### FULL_COVERAGE

`X_LONG_EXIT_T70_M0_P1`

Predicates:

- `RCI9 >= 70`;
- current open is above EMA20 in ATR14-normalized terms.

Observed source fidelity:

- source exits: `17 / 17` = `100%`
- ACTIVE_LONG control fires: `12 / 223` = `5.38%`

### BALANCED_COVERAGE

`X_LONG_EXIT_T70_M1_P0`

Predicates:

- `RCI9 >= 70`;
- EMA30 four-bar slope is positive.

Observed source fidelity:

- source exits: `15 / 17` = `88.24%`
- ACTIVE_LONG control fires: `10 / 223` = `4.48%`

No Pareto grammar occupied the 90% to below-100% LONG high-coverage tier. The tier remained empty.

## 4. Advanced SHORT-exit variants

### FULL_COVERAGE

`X_SHORT_EXIT_T70_M0_P0`

- `RCI9 <= -70`
- source exits: `10 / 10` = `100%`
- ACTIVE_SHORT control fires: `18 / 168` = `10.71%`

### HIGH_COVERAGE

`X_SHORT_EXIT_T70_M0_P1`

- `RCI9 <= -70`;
- four-bar fully closed return is negative.
- source exits: `9 / 10` = `90%`
- controls: `16 / 168` = `9.52%`

### BALANCED_COVERAGE

`X_SHORT_EXIT_T70_M1_P1`

- `RCI9 <= -70`;
- EMA20 four-bar slope is negative;
- four-bar fully closed return is negative.
- source exits: `8 / 10` = `80%`
- controls: `15 / 168` = `8.93%`

## 5. Interpretation boundary

The `70` threshold is retained as a transparent source-fidelity support boundary. It is not a profitability-optimized threshold.

Lower control-fire rate does not mean fewer losing trades. ACTIVE controls are non-source windows, not loss labels. None of these variants is a trading candidate or deployment decision.

## 6. Accepted artifact

- package: `BCR05D_OUTCOME_BLIND_FINITE_EXIT_GRAMMAR_20260730.zip`
- SHA256: `b1c4c66454f3076ffc90b22cac27280c6daa38f97db63ae07bed5294eed872d7`
- deterministic two-run SHA match: true

## 7. Decision

BCR05D passes. The two LONG and three SHORT exit variants may be combined with the frozen BCR05B entry variants in a complete state-machine replay. Component thresholds are not changed after integration results are observed.
