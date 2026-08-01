# GOLD UNCOVERED V1 — Research Preregistration

Created: 2026-08-02  
Status: `FROZEN_BEFORE_SOURCE_AUDIT_AND_BEFORE_OUTCOMES`

## 1. Research question

Can an independent causal event family add a structurally different GOLD candidate in regions not targeted by V19 or Challenger C1, without using either system as an input?

This protocol is for discovery, not deployment.

## 2. Independence definition

Candidate generation may use only raw closed candles and causal features derived from those candles.

It may not use:

- E40 chosen direction, raw score, percentile rank, model boundary, or calibration;
- V17/V18/V19 aggregate wave-state labels;
- V19/C1 entry timestamps, open intervals, trade outcomes, runtime state, or Discord state;
- any rule of the form “enter because V19 did not enter” or “enter opposite V19.”

V19/C1 may be compared only after a new candidate formula is frozen, and then only as a post-hoc overlap/additivity audit.

## 3. Source phase

Phase 0 validates raw candle authority before any feature, label, or outcome calculation.

Required source families:

- historical broker candles: M1, M5, M15, H1, H4;
- appended sharp candles: M1, M5, H1, H4;
- D1 is optional during Phase 0 and cannot silently become required later;
- sharp M15 may be absent and must not be guessed from another file.

The source audit records SHA256, schema, rows, first/last time, duplicates, monotonicity, candidate-path ambiguity, and exact old/sharp overlap on shared OHLCV/spread columns.

## 4. Outcome-blind discovery stages

### Phase 1 — causal feature and event catalogue

Define event kernels without labels or returns. The fixed families are:

1. `COMPRESSION_RELEASE`: multi-timeframe range/ATR compression followed by a closed-bar expansion or range escape.
2. `FAILED_BREAK_REVERSAL`: a causal prior-range break followed by a closed-bar reclaim, without future pivot confirmation.
3. `PULLBACK_RESUMPTION`: trend persistence plus a bounded retracement and causal resumption trigger, defined without E40 or V17 states.
4. `SESSION_TRANSITION`: broker-session restart/opening-range displacement and rejection/continuation using only already-observed session bars.
5. `VOLATILITY_STATE_CHANGE`: low-to-high or high-to-normal realized-volatility transition with a separate directional trigger.

These are families, not selectable profitable rules. Every parameter grid must be fixed before outcomes.

### Phase 2 — label-free density and redundancy

For each event definition, report only:

- total event count;
- count by calendar half-year, month, side, hour, and volatility bucket;
- spacing and clustering;
- overlap among GU1 event families;
- mechanical overlap with the structurally excluded formulas only if it can be computed from the new raw-feature implementation without reading V19/C1 outputs.

No TP/SL labels, returns, WR, PF, PnL, DD, or outcome-informed pruning are permitted.

Density gates are fixed in `discovery_contract_20260802.json`.

### Phase 3 — candidate freeze

Only event definitions that pass label-free density and non-redundancy gates may become fixed candidate proposals. Proposal selection must use structural interpretability and coverage, not returns.

Each proposal freezes:

- exact formula and parameters;
- side logic;
- entry timestamp;
- exact M1 execution contract;
- target/stop/horizon grid, if more than one value contract is preregistered;
- one-position accounting rule;
- all robustness gates.

### Phase 4 — outcome evaluation

Outcomes remain unavailable until Phase 3 artifacts are committed. Evaluation must be forward-sliced, direction-preserving, cost-stressed, exact-M1, and independently recalculated.

## 5. Fixed time separation

When outcomes are eventually authorized, fixed evaluation periods are:

- 2024H2
- 2025H1
- 2025H2
- 2026H1
- the separately frozen post-2026H1 extension available at Phase 3

No period may be deleted because it performs poorly.

## 6. Prohibited rescue behavior

After any outcome is inspected, do not:

- alter event thresholds;
- delete LONG or SHORT;
- choose a favorable hour, month, volatility bucket, or event subfamily;
- change TP/SL/horizon;
- add V19/C1 filters;
- relax a formal gate;
- rename a failed formula and rerun it as a new discovery.

A failed proposal remains failed. A materially new proposal requires a new preregistration and outcome-blind phase.

## 7. Interpretation cap

Even a complete retrospective pass is capped at:

`RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_ONLY`

It does not authorize Shadow, Discord, AI, MT5 orders, live trading, or promotion.
