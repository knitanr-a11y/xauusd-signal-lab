# BTC BCR05C — outcome-blind exit and state-signature contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `CONTRACT_FROZEN_IMPLEMENTATION_NEXT`
- profitability outcomes: forbidden

## 1. Why exit research is mandatory

BCR05B produced finite entry-fidelity variants, but BCR02A showed a path-dependent failure:

1. an exit is delayed or missed;
2. proxy state remains ACTIVE after source state returns to IDLE;
3. a later genuine primary entry arrives;
4. an otherwise correct entry condition is rejected because proxy state is wrong;
5. divergence cascades.

An integrated Track A candidate cannot be frozen from entry logic alone.

## 2. Frozen input populations

Input BCR04 package SHA256:

`5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`

### LONG-position exit analysis

- positive rows: `17` `VALID_LONG_EXIT_EVENT`
- controls: `223` core-feature-eligible `ACTIVE_LONG_NON_EVENT_CONTROL`

### SHORT-position exit analysis

- positive rows: `10` `VALID_SHORT_EXIT_EVENT`
- controls: `168` core-feature-eligible `ACTIVE_SHORT_NON_EVENT_CONTROL`

LONG and SHORT exits are analyzed separately. IDLE and opposite-state controls are not mixed into an exit comparison.

## 3. Exact-boundary causal analysis

At the source exit decision boundary use only:

- fully closed M15 history;
- current M15 open;
- source state before the event for population definition only;
- boundary-known gap flags.

Never use current M15 high, low or close.

## 4. Frozen feature families

### X1. RCI exit shape

- RCI9, RCI14 and RCI18 levels;
- one-bar deltas;
- turn-up and turn-down flags;
- fixed BCR05A RCI zones;
- direction-opposite turn prevalence:
  - LONG exit: RCI9 turn-down;
  - SHORT exit: RCI9 turn-up.

No assumption is made that all RCI periods reverse simultaneously.

### X2. EMA and trend structure

- EMA alignment;
- EMA20-minus-EMA30 and EMA30-minus-EMA40 bps;
- fixed 1-, 4- and 8-bar EMA slopes.

### X3. Closed-bar reversal/displacement

- fixed 1-, 4- and 16-bar closed returns;
- previous closed body/range/wick ratios;
- current-open gap from previous close;
- fixed rolling high/low location.

### X4. Volatility context

- ATR14;
- ATR14/ATR50 ratio;
- realized-volatility 32-bar band;
- Bollinger-width band.

Volatility may be descriptive exit context, but no threshold becomes an exit rule in BCR05C.

### Fidelity context only

- source-state age;
- bars since previous genuine source event;
- existing M7C exact/late/missed classification.

These are not standalone future candidate predicates.

## 5. Statistics

Use the same frozen BCR05A framework:

- binary/categorical: prevalence, corrected odds ratio, Fisher exact p-value;
- continuous: median, IQR, median difference, Cliff's delta, two-sided Mann–Whitney U;
- Benjamini-Hochberg q = 0.10 within direction, family and statistic type;
- leave-one-exit-day-out and leave-one-exit-out effect-sign stability.

No high-capacity classifier, random split or continuous threshold search is allowed.

At most three additional exit feature families per position direction may be shortlisted. A minimum is not required.

## 6. One-bar-late timing audit

BCR02A found six older source exits reproduced one M15 bar late.

For every source exit with an exact next M15 decision row, BCR05C may inspect the next row only for timing explanation.

The next-row analysis must be labeled:

`POST_SOURCE_EXIT_ONE_BAR_TIMING_DESCRIPTIVE_ONLY`

It may report:

- whether a direction-opposite RCI turn appears one bar later;
- whether RCI level or delta crosses a fixed zone one bar later;
- whether an existing M7C threshold passes one bar later;
- whether the next row would still be in the proxy ACTIVE state.

It may not use the post-event row as an exact-time candidate feature or profitability input.

## 7. Exact, late and missed decomposition

Where accepted M7C comparison evidence exists, keep separate:

- exact exit match;
- one-M15-bar-late match;
- missed exit;
- proxy/source state already divergent before exit;
- data-gap or unavailable-feature case.

Do not aggregate exact and late into one successful category without showing both counts.

## 8. State divergence consequence ledger

For each source exit, build an outcome-blind consequence ledger containing:

- source state before and after exit;
- proxy state at exact exit boundary;
- proxy state one bar later;
- first later boundary at which source and proxy states resynchronize;
- number of decision bars divergent;
- later genuine primary entries encountered while divergent;
- whether those entries were rejected only because proxy state remained ACTIVE;
- event IDs and timestamps, not trade outcomes.

This ledger explains path dependence. It must not attach future price returns or win/loss labels.

## 9. Required outputs

- LONG-exit-versus-ACTIVE_LONG comparison tables;
- SHORT-exit-versus-ACTIVE_SHORT comparison tables;
- FDR and effect-size manifest;
- leave-out stability report;
- one-bar-late timing report;
- exact/late/missed M7C decomposition;
- state-divergence consequence ledger;
- exit feature-family shortlist;
- non-shortlisted family reasons;
- integrity proof of no outcome access.

## 10. What BCR05C does not do

- no final exit formula;
- no time stop;
- no TP/SL;
- no holding-period optimization;
- no claim that earlier exit is more profitable;
- no resynchronization policy selection;
- no integrated candidate;
- no FF06 or shadow.

## 11. Required later stages

After BCR05C:

1. preregister a finite exit grammar;
2. replay entry and exit variants as complete state machines;
3. compare source recall, extra transitions, state-divergence duration and missed-primary cascades;
4. freeze a small integrated source-fidelity family;
5. only then define a separate trading-value/outcome gate.

## 12. Runtime protection

Collector, M7C, M8C, M9 and M10 remain running and unchanged. GOLD/MOCHIPOYO write-back, Discord, MT5 order and live-ready actions remain forbidden.
