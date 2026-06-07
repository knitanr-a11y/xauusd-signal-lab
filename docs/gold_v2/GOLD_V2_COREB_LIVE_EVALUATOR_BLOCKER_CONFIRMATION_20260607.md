# GOLD V2 CoreB live evaluator blocker confirmation

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Confirmation from prior-chat review

The prior-chat review returned the following conclusion:

```text
CoreB historical backtest is reproduced.
However, regenerating CoreB RR125_BUY_CONFLUENCE from OHLC as a live evaluator remains blocked because same_count / cluster_id / membership source-of-truth generation evidence is insufficient.
```

This matches the existing 13C / 13C-2 / 13C-3 / 13C-5 audit conclusion.

## 2. Current CoreB status

```text
CoreB historical SOT/backtest: reproduced / allowed for historical reporting
CoreB live evaluator: blocked
CoreB same_count approximation: forbidden
```

## 3. Why CoreB live evaluator is blocked

CoreB RR125_BUY_CONFLUENCE depends on:

```text
same_count >= 15
cluster_id / cluster membership semantics
RR125 BUY confluence source universe
```

The historical/backtest result can be reproduced from the SOT rows, but the live evaluator must regenerate the signal from OHLC and features at the current confirmed M15 close.

Current artifacts do not contain enough source-of-truth evidence for how `same_count`, `cluster_id`, or row-level cluster membership were generated.

Previous audits showed that candidate replay from available rules produced far fewer rows than the historical CoreB SOT target, and approximate reconstructions did not prove parity.

## 4. Required evidence to unblock CoreB live evaluator

At least one of the following is required:

```text
1. Original CoreB same_count / clustering script
2. Original cluster_id / cluster membership generator
3. Row-level cluster membership ledger
4. same_count_source_universe intermediate CSV with sufficient membership semantics
5. A complete per-CoreB-row evidence package explaining same_count / cluster_id / membership derivation
```

Without this, CoreB live evaluator must remain blocked.

## 5. Forward policy

Do not implement a guessed same_count.
Do not replace cluster membership with static windows, connected components, raw entry-time counts, or approximate confluence counts.
Do not treat historical CoreB SOT rows as future/live signals.

CoreB may remain available for historical SOT reporting, portfolio accounting, and documentation, but not for live evaluator generation until source-of-truth clustering evidence is recovered.

## 6. Impact on 25A and later

25A should classify CoreB as:

```text
component = CoreB RR125_BUY_CONFLUENCE
historical_status = REPRODUCED_HISTORICAL_SOT_ALLOWED
live_evaluator_status = BLOCKED_SOURCE_CLUSTER_MEMBERSHIP_REQUIRED
recommended_action = DO_NOT_MAP_COREB_TO_LIVE_EVALUATOR_YET
```

Recommended work order:

```text
1. Prioritize MEDIUM feature/asof parity and TIER2 reconciliation.
2. In parallel, continue CoreA A-gate executable source freeze.
3. Keep CoreB live evaluator blocked unless original clustering/membership evidence is found.
```
