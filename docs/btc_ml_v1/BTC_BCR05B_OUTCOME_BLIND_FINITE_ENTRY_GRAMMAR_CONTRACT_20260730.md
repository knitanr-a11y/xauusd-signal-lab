# BTC BCR05B — outcome-blind finite Track A entry grammar contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `CONTRACT_FROZEN_IMPLEMENTATION_NEXT`
- profitability outcomes: forbidden

## 1. Purpose

BCR05B converts the BCR05A source-signature evidence into a small finite set of entry grammars.

It measures source-event recall and non-event control firing only. It does not select a profitable strategy, define an exit, construct TP/SL, or authorize a trade candidate.

## 2. Frozen input

- BCR04 package SHA256: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- BCR05A corrected package SHA256: `b49b9118d0e15184d8b7aea3452b70899ed0406b82360580fd076ae972d9255b`
- LONG primary source events: `16`
- SHORT primary source events: `10`
- eligible IDLE controls: `438`

Only causally available market features are used. Source-event distance, next-event information, source-state age and other source-derived fidelity context are excluded from grammar predicates.

## 3. Mandatory anchor

Every grammar requires the direction-correct RCI9 turn:

- LONG: `RCI9_TURN_UP`
- SHORT: `RCI9_TURN_DOWN`

The anchor is calculated from fully closed M15 bars under the BCR04 contract.

## 4. Three optional gate axes

### 4.1 EMA gate

- `E0`: no EMA gate
- `E1`: direction-correct stack
  - LONG: EMA20 > EMA30 > EMA40
  - SHORT: EMA20 < EMA30 < EMA40

### 4.2 RCI9 level gate

Fixed boundaries come from the preregistered BCR05A RCI zones. No threshold search is allowed.

- `Z0`: no level gate
- `Z1_POLARITY`
  - LONG: RCI9 <= 0
  - SHORT: RCI9 >= 0
- `Z2_EXTREME`
  - LONG: RCI9 <= -40
  - SHORT: RCI9 >= 40

### 4.3 Previous fully closed return gate

- `P0`: no return-sign gate
- `P1`: direction-matching previous closed M15 return
  - LONG: closed return 1 bar > 0
  - SHORT: closed return 1 bar < 0

No magnitude threshold is used. The return gate and RCI delta are recognized as correlated responses to the newest closed bar; they are not counted as independent confirmations.

## 5. Exact grammar count

Cartesian product:

- EMA: 2 states
- RCI level: 3 states
- return sign: 2 states

Total:

- `12` LONG grammars
- `12` SHORT grammars
- `24` directional grammar evaluations

Grammar ID format:

`A_<DIRECTION>_<E0|E1>_<Z0|Z1|Z2>_<P0|P1>`

No grammar may be added, removed, merged or rescued after the output is inspected.

## 6. Evaluation populations

### LONG

- positive rows: all 16 `PRIMARY_LONG_EVENT`
- negative/control rows: all 438 core-feature-eligible `IDLE_NON_EVENT_CONTROL`

### SHORT

- positive rows: all 10 `PRIMARY_SHORT_EVENT`
- negative/control rows: the same 438 controls

No event is dropped because it fails a strict grammar.

## 7. Metrics

For each grammar report:

- source-event hits and recall;
- control hits and control-fire rate;
- specificity;
- event-to-control prevalence difference;
- corrected odds ratio;
- Fisher exact p-value, descriptive only;
- source-event density among all grammar fires;
- number of gates;
- exact predicates.

No profitability metric is permitted.

## 8. Pareto and advancement rules

### 8.1 Pareto frontier

A grammar is dominated when another grammar has:

- equal or higher source recall; and
- equal or lower control-fire rate;

with at least one strict improvement.

Only nondominated grammars enter the Pareto report.

### 8.2 Recall tiers

At most three grammars per direction may advance to the later integrated fidelity stage.

Select at most one per tier:

1. `FULL_COVERAGE`: recall = 100%
2. `HIGH_COVERAGE`: recall >= 90% and < 100%
3. `BALANCED_COVERAGE`: recall >= 75% and < 90%

Within each tier choose:

1. lowest control-fire rate;
2. then fewer optional gates;
3. then lexical grammar ID.

If a tier has no grammar, it remains empty. Do not lower the threshold to fill it.

A grammar outside the Pareto frontier cannot advance even if it is the best within a recall tier.

## 9. Stability report

For every advancing grammar report:

- leave-one-primary-event-calendar-day-out recall range;
- leave-one-primary-event-out recall range;
- control-fire rate by UTC calendar day;
- event hits by source-event day;
- whether all hits come from one day.

This remains source-fidelity stability, not OOS profitability.

## 10. Interpretation constraints

BCR05B may conclude:

- which finite grammars reproduce more or fewer genuine source entries;
- how much each gate suppresses ordinary IDLE controls;
- which grammars are Pareto efficient under source fidelity.

BCR05B may not conclude:

- which grammar earns money;
- whether lower control-fire rate reduces losing trades;
- which grammar should be deployed;
- whether a missed source event is desirable.

A strict grammar that misses source events is not automatically better.

## 11. Next system dependency

Entry fidelity alone is insufficient because BCR02A showed state divergence caused by delayed or missed exits.

After BCR05B, the next required stage is an outcome-blind exit/state analysis. No integrated Track A candidate formula may be frozen until entry and exit/state contracts are both completed.

## 12. Explicitly forbidden

- outcomes, WR, PF, DD, MFE, MAE;
- TP/SL or holding-period optimization;
- continuous threshold tuning;
- adding ATR, compression or time gates;
- source-event-distance predicates;
- source-state-age predicates in a standalone candidate;
- FF06;
- prospective start;
- shadow runtime;
- Discord or MT5 orders;
- modification of Collector, M7C, M8C, M9 or M10.
