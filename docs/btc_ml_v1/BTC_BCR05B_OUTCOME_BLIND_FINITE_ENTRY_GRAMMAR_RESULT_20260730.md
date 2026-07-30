# BTC BCR05B — outcome-blind finite entry grammar result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `READY_OUTCOME_BLIND_FINITE_ENTRY_GRAMMAR_FIDELITY_RESULT`
- profitability outcomes: not opened
- integrated candidate: not frozen

## 1. Frozen design

BCR05B evaluated exactly:

- 12 LONG grammars;
- 12 SHORT grammars;
- 24 total.

Every grammar required the direction-correct RCI9 turn. The only optional axes were:

- direction-correct EMA stack: off/on;
- RCI9 level: none, polarity, fixed extreme ±40;
- previous fully closed M15 return sign: off/on.

No ATR, compression, hour, weekday, source-event distance, source-state age or continuous threshold was added.

Input BCR04 package SHA256:

`5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`

## 2. Evaluation populations

- LONG primary source events: `16`
- SHORT primary source events: `10`
- compatible core-feature-eligible IDLE controls: `438`

All events and all controls remained in the denominators for every grammar.

## 3. Pareto frontier

A grammar was Pareto efficient when no other grammar had both:

- equal or higher source-event recall; and
- equal or lower IDLE-control fire rate;

with at least one strict improvement.

Pareto rows:

- LONG: `3`
- SHORT: `4`

The frozen recall-tier rule advanced five variants total.

## 4. LONG variants advanced

### FULL_COVERAGE

`A_LONG_E0_Z1_P0`

Predicates:

- RCI9 turn-up;
- RCI9 <= 0.

Observed source fidelity:

- source hits: `16 / 16`
- recall: `100%`
- control hits: `29 / 438`
- control-fire rate: `6.62%`
- source-event density among fires: `35.56%`
- event days represented: `8`
- single-day dominance: false

This is the highest-coverage source approximation, not a trading signal with proven value.

### HIGH_COVERAGE

No Pareto grammar had recall from 90% to below 100%. The tier remains empty. The threshold was not lowered.

### BALANCED_COVERAGE

`A_LONG_E1_Z2_P0`

Predicates:

- RCI9 turn-up;
- bullish EMA20 > EMA30 > EMA40;
- RCI9 <= -40.

Observed source fidelity:

- source hits: `13 / 16`
- recall: `81.25%`
- control hits: `0 / 438`
- control-fire rate: `0%`
- source-event density among fires: `100%` in this source interval
- event days represented: `7`
- single-day dominance: false

Zero control hits in 438 rows is not a claim of future zero false positives and not evidence of profitability.

Another LONG Pareto grammar, `A_LONG_E1_Z1_P0`, had 87.5% recall and 2 control hits. It occupied the same balanced tier. The frozen tie-break selected the zero-control grammar rather than changing the tier rule after seeing results.

## 5. SHORT variants advanced

### FULL_COVERAGE

`A_SHORT_E0_Z1_P1`

Predicates:

- RCI9 turn-down;
- RCI9 >= 0;
- previous fully closed M15 return < 0.

Observed source fidelity:

- source hits: `10 / 10`
- recall: `100%`
- control hits: `42 / 438`
- control-fire rate: `9.59%`
- source-event density among fires: `19.23%`
- event days represented: `5`
- single-day dominance: false

### HIGH_COVERAGE

`A_SHORT_E1_Z1_P1`

Predicates:

- RCI9 turn-down;
- bearish EMA20 < EMA30 < EMA40;
- RCI9 >= 0;
- previous fully closed M15 return < 0.

Observed source fidelity:

- source hits: `9 / 10`
- recall: `90%`
- control hits: `9 / 438`
- control-fire rate: `2.05%`
- source-event density among fires: `50%`
- event days represented: `5`
- single-day dominance: false

### BALANCED_COVERAGE

`A_SHORT_E1_Z2_P0`

Predicates:

- RCI9 turn-down;
- bearish EMA stack;
- RCI9 >= 40.

Observed source fidelity:

- source hits: `8 / 10`
- recall: `80%`
- control hits: `2 / 438`
- control-fire rate: `0.46%`
- source-event density among fires: `80%`
- event days represented: `5`
- single-day dominance: false

`A_SHORT_E1_Z2_P1` had identical source and control counts, but used one additional optional gate. The frozen tie-break therefore retained `P0`.

## 6. Stability

All five advancing grammars retained event hits across multiple source-event days. None depended on one calendar day.

Leave-one-event-day and leave-one-event recall ranges were recorded in the package. They measure source-fidelity sensitivity only, not future trading stability.

## 7. What is not concluded

BCR05B does not establish:

- that a strict grammar is more profitable;
- that a lower control-fire rate means fewer losing trades;
- that a missed source event should be excluded;
- that zero observed control hits will persist;
- that any of the five variants should be deployed.

Control rows are non-event source windows, not losing-trade labels.

## 8. Accepted artifacts

Package:

- file: `BCR05B_OUTCOME_BLIND_FINITE_ENTRY_GRAMMAR_20260730.zip`
- SHA256: `525be07cab36d9582637a5db523d16f876a4d7cc06b1103bfdc14b29dcec65c9`
- deterministic second-run SHA match: true

Implementation:

- `scripts/btc_ml_v1/BCR05B_outcome_blind_finite_entry_grammar/python/run_bcr05b_finite_entry_grammar.py`
- commit: `7343e1d1a872f9d7666fabac5652dbfd45c3154e`
- local script SHA256: `8c38095f07f00a8bb1320773fd0ef3e13d415aedfd39f38e55b8bb609b972f93`

Tests:

- `tests/btc_ml_v1/test_bcr05b_finite_entry_grammar.py`
- corrected test commit: `22e6df2a3bd55c30c39f5d0715175d3006004d0a`
- result: `4 passed`

## 9. Required next stage

Entry fidelity cannot be integrated into a candidate yet.

BCR02A showed that delayed or missed exits leave the proxy in the wrong state, causing later valid entries to be rejected. The next stage must therefore analyze exit signatures and state-path consequences without opening profitability outcomes.

Required next:

`BCR05C_OUTCOME_BLIND_EXIT_AND_STATE_SIGNATURE_ANALYSIS`

Only after entry and exit/state grammar families are frozen may an integrated Track A source-fidelity state machine be assembled. Trading value remains a later, separate gate.
