# BTC BCR05A — outcome-blind Track A source-signature comparison contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `CONTRACT_FROZEN_IMPLEMENTATION_NEXT`
- outcome interpretation: forbidden

## 1. Purpose

BCR05A asks which pre-decision features distinguish genuine BTC primary source alerts from compatible non-event decision windows.

It does not ask whether any alert wins money. It does not construct TP/SL, choose a trading candidate, or promote a formula.

## 2. Frozen input

- BCR04 package SHA256: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- decision rows: `907`
- core-feature-eligible rows: `905`
- primary LONG events: `16`
- primary SHORT events: `10`
- IDLE non-event controls: `440`, of which `438` are core-feature eligible

Only `PRIMARY_LONG_EVENT`, `PRIMARY_SHORT_EVENT` and core-feature-eligible `IDLE_NON_EVENT_CONTROL` rows enter the primary-entry signature comparison.

ACTIVE-state controls are not mixed into primary-entry analysis. Exit, reentry and opposite-ignored events remain preserved but are analyzed separately later.

## 3. Known anchor versus new evidence

The direction-correct RCI9 turn is already established outcome-blind evidence:

- LONG primary: RCI9 turn-up;
- SHORT primary: RCI9 turn-down.

BCR05A must not present this as a newly discovered result. It is the frozen anchor whose specificity against IDLE controls is measured.

The purpose of BCR05A is to determine whether a small number of additional feature families improve source-fidelity discrimination without outcome access.

## 4. No high-capacity model

Forbidden:

- random forest, gradient boosting, neural network or unconstrained classifier;
- random train/test split;
- exhaustive threshold search;
- recursive feature elimination;
- selecting a rule because it produces a preferred event count;
- using source exits or later prices as labels;
- using profitability or trade outcomes.

The event sample is too small for a credible high-capacity model.

## 5. Frozen feature families

### A. RCI shape

- RCI9 level and delta1;
- RCI14 level and delta1;
- RCI18 level and delta1;
- direction-correct RCI turn prevalence;
- fixed RCI level zones: `<=-80`, `(-80,-40]`, `(-40,0]`, `(0,40)`, `[40,80)`, `>=80`.

### B. EMA structure

- EMA alignment: bullish, bearish, mixed;
- EMA20-minus-EMA30 bps;
- EMA30-minus-EMA40 bps;
- fixed 1-, 4- and 8-bar EMA slopes.

### C. Volatility and compression

- ATR14;
- ATR14/ATR50 ratio;
- preregistered ATR14 quintile;
- realized-volatility 32-bar quintile;
- Bollinger-width 20 quintile.

### D. Closed-bar and location context

- fixed 1-, 4- and 16-bar returns;
- previous closed-bar range/body/wick ratios;
- current-open gap from previous close;
- distance to fixed rolling high/low;
- fixed breakout/location flags already present in BCR04.

### E. Clock and source sequence context

- broker-server hour;
- day of week;
- source-state age bin;
- distance to nearest source event bin;
- gap-in-lookback indicators.

No new feature family may be added after comparison output is opened without a recorded correction stage.

## 6. Comparison populations

Run LONG and SHORT separately.

### LONG

- positive: all 16 `PRIMARY_LONG_EVENT` rows;
- control: all 438 core-feature-eligible `IDLE_NON_EVENT_CONTROL` rows.

### SHORT

- positive: all 10 `PRIMARY_SHORT_EVENT` rows;
- control: the same 438 core-feature-eligible `IDLE_NON_EVENT_CONTROL` rows.

Also report deterministic descriptive strata by ATR quintile, EMA alignment, broker hour and source-event-distance bin. These strata do not replace the full control universe.

## 7. Statistics

### Binary and categorical features

Report:

- event prevalence;
- control prevalence;
- prevalence difference;
- odds ratio with Haldane-Anscombe 0.5 correction when required;
- two-sided Fisher exact p-value.

### Continuous features

Report:

- event median and interquartile range;
- control median and interquartile range;
- median difference;
- Cliff's delta.

No continuous threshold is selected in BCR05A.

### Multiple testing

Apply Benjamini-Hochberg correction at `q=0.10` separately within:

- direction: LONG or SHORT;
- feature family: A through E;
- statistic type: binary/categorical or continuous.

Raw p-values are retained. Failure to pass FDR is not rescued by an attractive descriptive difference.

## 8. Temporal stability

For each feature family, run leave-one-primary-event-calendar-day-out descriptive stability.

A feature is stable only when:

- the direction of its event-control effect does not reverse materially in most leave-one-day-out runs; and
- its apparent effect is not created by one calendar day or one event.

This is not an OOS profitability test. It is a source-fidelity robustness check.

## 9. Shortlist rule

RCI9 direction-correct turn remains the anchor regardless of significance because it is prior established evidence.

For each direction, at most three additional feature families may be shortlisted for the later finite grammar stage.

A family may be shortlisted only when:

1. at least one preregistered feature has a nontrivial effect size;
2. the effect survives the declared FDR group or is explicitly retained as descriptive-only;
3. leave-one-day-out direction is reasonably stable;
4. no single event creates the effect;
5. the feature is available under the BCR04 causal contract.

If no family qualifies, the correct result is anchor-only or no-addition. A minimum number of additions is not required.

## 10. Required outputs

- LONG event-versus-IDLE-control comparison table;
- SHORT event-versus-IDLE-control comparison table;
- categorical prevalence tables;
- continuous effect-size tables;
- FDR adjustment manifest;
- leave-one-event-day-out stability report;
- feature-family shortlist with reasons;
- non-shortlisted inventory with reasons;
- integrity proof that no outcome field was opened.

## 11. Explicitly not authorized

- final trigger formula;
- candidate performance evaluation;
- win rate, PF, DD, MFE or MAE;
- TP/SL or exit optimization;
- M5 execution design;
- H1 regime features;
- FF06;
- shadow runtime;
- Discord or MT5 order actions;
- modification of Collector, M7C, M8C, M9 or M10.

BCR05A completion permits only a later finite Track A grammar preregistration. It does not permit profitability evaluation.
