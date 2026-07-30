# BTC BCR05F — Track A source-fidelity family freeze

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T18:45:00+09:00`
- status: `TRACK_A_FOUR_MEMBER_SOURCE_FIDELITY_FAMILY_FROZEN`
- trading value: not evaluated
- deployable candidate count: zero

## 1. Why four variants are retained

BCR05E produced four non-dominated complete state machines. No one profile dominates all others on source recall, extra transitions, state agreement and state-blocked primary count.

Selecting one now would silently convert a source-fidelity preference into an assumed profitability preference. That is forbidden.

The four Pareto variants are therefore frozen together for the later trading-value gate.

## 2. Frozen Track A family

### `TRACK_A_F1_COVERAGE_FIRST`

`I__A_LONG_E0_Z1_P0__A_SHORT_E0_Z1_P1__X_LONG_EXIT_T70_M0_P1__X_SHORT_EXIT_T70_M0_P0`

Role: maximum source-transition coverage.

### `TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE`

`I__A_LONG_E0_Z1_P0__A_SHORT_E1_Z1_P1__X_LONG_EXIT_T70_M0_P1__X_SHORT_EXIT_T70_M0_P0`

Role: reduce extra transitions while retaining very high source recall.

### `TRACK_A_F3_STATE_FIDELITY`

`I__A_LONG_E1_Z2_P0__A_SHORT_E1_Z2_P0__X_LONG_EXIT_T70_M0_P1__X_SHORT_EXIT_T70_M0_P0`

Role: maximize source-state agreement and minimize total divergent boundaries among the retained family.

### `TRACK_A_F4_MINIMUM_EXTRA_PARETO`

`I__A_LONG_E1_Z2_P0__A_SHORT_E1_Z2_P0__X_LONG_EXIT_T70_M1_P0__X_SHORT_EXIT_T70_M0_P0`

Role: minimum observed extra-transition count among the non-dominated family.

## 3. Immutable component definitions

Entry and exit predicates remain exactly as recorded by BCR05B and BCR05D.

No threshold, EMA gate, return gate, conflict policy or state transition may be changed after future profitability output is opened. Any changed formula becomes a new family and a new trial.

## 4. Standalone initialization boundary

The source-seeded BCR05E replay was a fidelity diagnostic only.

Every trading-value evaluation and any future standalone shadow must:

- initialize in `IDLE`;
- use only its own emitted transitions to change state;
- never read source state;
- never force a reset merely because a source event occurred;
- report initialization/convergence effects separately.

The M7C/source state is not a deployable input.

## 5. Causal signal boundary

At each M15 decision boundary the family may use:

- all fully closed M15 history before the current bar open;
- the current M15 open;
- deterministic features frozen in BCR04;
- explicit gap/unavailable flags.

It may not use:

- current M15 high, low or close;
- future bars;
- interpolated gaps;
- uncontracted higher-timeframe data;
- source event labels or source state in value evaluation;
- outcome fields in signal generation.

## 6. Exposure classification

The source interval from `2026-07-20T15:00:00Z` through `2026-07-30T01:30:00Z` was used to design and freeze this family.

It is design-exposed and cannot be described as independent OOS profitability evidence.

Historical evaluation before the freeze may only be called retrospective walk-forward evidence. Independent prospective evidence begins only after:

1. formulas remain frozen;
2. execution and cost contracts are frozen;
3. a new prospective start is committed;
4. no backfill or reset is allowed.

## 7. Later value gate

All four variants must enter the same value gate. The value gate must predefine:

- exact entry and exit observation price;
- spread, commission and slippage treatment;
- gap and missing-row behavior;
- one-position semantics;
- same-boundary conflict behavior;
- historical split and trial correction;
- minimum trade count and concentration checks;
- promotion, hold and rejection rules.

No profile may receive a more favorable execution assumption.

## 8. Track B requirement

Track A alone is not the final system.

Before final portfolio promotion, at least one genuinely independent Track B mechanism family must be built and evaluated under the same causal and value contracts. A parameter variation of the RCI/EMA source family does not count as Track B.

## 9. Decision

The four-member Track A source-fidelity family is frozen. None is a trading candidate yet. Next work resumes outcome-blind Track B mechanism research and prepares a shared, separate trading-value contract.
