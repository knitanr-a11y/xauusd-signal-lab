# BTC BCR05E — outcome-blind integrated entry/exit state-machine replay result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T18:40:00+09:00`
- status: `READY_OUTCOME_BLIND_INTEGRATED_SOURCE_FIDELITY_REPLAY`
- profitability outcomes: not opened
- trading candidate promoted: no

## 1. Frozen integration

BCR05E combined:

- 2 LONG-entry variants;
- 3 SHORT-entry variants;
- 2 LONG-exit variants;
- 3 SHORT-exit variants.

Total complete state machines: `36`.

Every variant used the same one-position state machine:

- IDLE may enter LONG or SHORT;
- ACTIVE_LONG may only emit LONG_EXIT;
- ACTIVE_SHORT may only emit SHORT_EXIT;
- reentries and opposite alerts do not change candidate state;
- simultaneous LONG/SHORT entry predicates produce no transition.

Component thresholds were not changed after replay results were observed.

Inputs:

- BCR04: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- BCR05B: `525be07cab36d9582637a5db523d16f876a4d7cc06b1103bfdc14b29dcec65c9`
- BCR05C: `221280603569054f3ffc23c6698446e377f9d650d288fa3d08d224a8e3925af3`
- BCR05D: `b1c4c66454f3076ffc90b22cac27280c6daa38f97db63ae07bed5294eed872d7`
- replay-contract commit: `180d228983561b4fa3f4e8d00fab6cd08a0538c7`

## 2. Seed separation

The primary source-fidelity replay used the known pre-prospective source state as an analysis seed. This isolates formula/state-path fidelity.

A second IDLE-seeded replay was produced for standalone-initialization diagnosis. The source seed is explicitly not claimed as a deployable live requirement.

## 3. Four non-dominated integrated variants

Four source-seeded variants remained Pareto efficient on:

- exact supported-transition recall;
- extra transition rate;
- divergent boundary count;
- state-blocked primary count.

### F1 — maximum coverage

`I__A_LONG_E0_Z1_P0__A_SHORT_E0_Z1_P1__X_LONG_EXIT_T70_M0_P1__X_SHORT_EXIT_T70_M0_P0`

- exact supported transitions: `51 / 53` = `96.23%`
- extra transitions: `66` = `7.28%` of 907 boundaries
- source-state agreement: `482 / 907` = `53.14%`
- divergent boundaries: `425`
- divergence episodes: `29`
- maximum divergence episode: `46` bars
- state-blocked source primaries: `1`

Transition recall:

- PRIMARY_LONG: `93.75%`
- PRIMARY_SHORT: `100%`
- LONG_EXIT: `100%`
- SHORT_EXIT: `90%`

This variant maximizes source-transition coverage but produces many additional transitions and spends almost half the interval in a different state from the source.

### F2 — high-coverage intermediate

`I__A_LONG_E0_Z1_P0__A_SHORT_E1_Z1_P1__X_LONG_EXIT_T70_M0_P1__X_SHORT_EXIT_T70_M0_P0`

- exact supported transitions: `50 / 53` = `94.34%`
- extra transitions: `37` = `4.08%`
- state agreement: `70.67%`
- divergent boundaries: `266`
- divergence episodes: `15`
- maximum divergence episode: `65` bars
- state-blocked primaries: `1`

This middle variant gives up one supported transition relative to F1 while materially reducing extras and total divergence.

### F3 — state-fidelity profile

`I__A_LONG_E1_Z2_P0__A_SHORT_E1_Z2_P0__X_LONG_EXIT_T70_M0_P1__X_SHORT_EXIT_T70_M0_P0`

- exact supported transitions: `45 / 53` = `84.91%`
- extra transitions: `16` = `1.76%`
- state agreement: `75.74%`
- divergent boundaries: `220`
- divergence episodes: `8`
- maximum divergence episode: `116` bars
- state-blocked primaries: `1`

This variant has the best total state agreement and fewest divergent boundaries, but its longest single divergence episode is larger and it misses more supported transitions.

### F4 — minimum-extra Pareto profile

`I__A_LONG_E1_Z2_P0__A_SHORT_E1_Z2_P0__X_LONG_EXIT_T70_M1_P0__X_SHORT_EXIT_T70_M0_P0`

- exact supported transitions: `40 / 53` = `75.47%`
- extra transitions: `15` = `1.65%`
- state agreement: `67.14%`
- divergent boundaries: `298`
- divergence episodes: `8`
- maximum divergence episode: `116` bars
- state-blocked primaries: `2`

F4 has only one fewer extra transition than F3 but substantially worse recall and more divergence. It remains Pareto only because its extra count is the minimum.

## 4. Why component results were not enough

The standalone entry and exit grammars had high event recall, but complete state replay changed their behavior materially.

For example, F1 uses full-coverage entry/exit components, yet complete replay recalls `51 / 53`, not `53 / 53`, because an earlier extra or missed transition changes the state in which a later predicate is evaluated.

This confirms that entry recall, exit recall and control-fire rate cannot be treated as independent candidate scores. Path-dependent state replay is mandatory.

## 5. IDLE-seed diagnostic

The primary profiles were also replayed from IDLE without using the source seed.

- F1 exact recall remained `96.23%`, divergent boundaries changed from `425` to `427`.
- F3 exact recall changed from `84.91%` to `83.02%`, divergent boundaries from `220` to `225`.
- F4 exact recall changed from `75.47%` to `73.58%`, divergent boundaries from `298` to `303`.

The source seed is therefore not the sole cause of the observed profile ordering, but any future standalone candidate must still use an explicit IDLE initialization contract.

## 6. What is not concluded

BCR05E does not establish:

- profitability of F1–F4;
- that extra transitions are bad trades;
- that maximum source recall is the best economic choice;
- that F3's state agreement implies higher expectancy;
- that F4 should be kept merely because it has one fewer extra;
- any TP, SL, time stop, position size or live policy.

No future return, win/loss, PF, DD, MFE, MAE or trade outcome was opened.

## 7. Accepted artifact

- package: `BCR05E_OUTCOME_BLIND_INTEGRATED_STATE_MACHINE_REPLAY_20260730.zip`
- SHA256: `d8fd13557f3b0a9c6d7fc9d499e7654ec4cb814f5538e41928b2e9d2c4d0ca84`
- deterministic two-run SHA match: true

## 8. Decision

BCR05E passes.

All four non-dominated variants are retained as a small Track A source-fidelity family. None is promoted as a trading candidate. The next work must keep two separate paths:

1. define a standalone, IDLE-seeded Track A trading-value gate with exact execution and cost contracts;
2. resume Track B independent-mechanism research so the final system is not only a family of Mochipoyo approximations.
