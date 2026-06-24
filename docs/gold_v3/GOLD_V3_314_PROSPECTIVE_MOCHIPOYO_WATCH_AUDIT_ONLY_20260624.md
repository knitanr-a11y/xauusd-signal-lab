# GOLD V3 Stage314 — Prospective Mochipoyo Research Watch

## Why Stage314 exists

Stage313 found a fixed two-track diversified research watch, but 2026 had already been inspected during Stages311–313. Further filter changes would therefore increase selection bias.

Stage314 freezes the rule set once and accepts only signals whose closed-M5 decision time is strictly later than the first-run cutoff. It does not backfill any earlier signal into prospective results.

## Frozen tracks

### Primary comparison track

- `MOCHI_HIDDEN_PULLBACK`
- LONG
- M5/H4
- quality score at least 8.0
- 1.5R target

This track passed the Stage312 2024–2025 gate but failed the Stage313 fragility-retention gate. It remains only as a fixed comparison component.

### Secondary research-watch track

- `MOCHI_EARLY_PULLBACK`
- SHORT
- M5/H4
- ATR ratio at least 1.0
- round-number-near entries excluded
- 1.5R target

This was the Stage313 low-frequency research watch with positive 2024, 2025, and 2026 historical results.

## Portfolio policy

- one position at a time
- no preemption
- primary priority before secondary only on the exact same entry timestamp
- a new entry is rejected while an accepted position remains open
- same-M1 TP/SL touch resolves as SL

## First-run freeze

The first successful run writes:

`stage314_mochipoyo_prospective_watch_contract.json`

The contract records the latest closed M1, M5, and H4 timestamps and freezes:

`decision_dt strictly greater than frozen latest closed M5 close_time`

Later runs must reuse the same contract. The cutoff is never moved forward and the contract is not silently regenerated.

## Closed-candle and outcome rules

- Stage289 `goldsharp_*.csv` closed-row contract is authoritative.
- The newest complete row is retained.
- The next exact closed M5 open is the entry.
- M1 is used for first-touch outcome evaluation.
- A trade is resolved only when TP, SL, or the full 720-minute horizon is known on closed M1 bars.
- Pending trades have no marked/as-of PnL.
- Pending trades are excluded from all metrics.
- Resolved metrics require `exit_dt <= latest closed M1 close_time`.

## Frozen future review gate

A future sample becomes eligible for human audit only after all of the following:

- at least 30 accepted resolved trades
- at least eight LONG trades
- at least eight SHORT trades
- PF at least 1.25
- positive total R
- maximum drawdown no more than 8R
- largest winner share no more than 35%

This gate never performs automatic promotion.

## Outputs

- `stage314_mochipoyo_prospective_watch_contract.json`
- `stage314_mochipoyo_prospective_watch.json`
- `stage314_mochipoyo_prospective_signals.csv`
- `stage314_mochipoyo_prospective_resolved.csv`
- `stage314_mochipoyo_prospective_pending.csv`

The first run normally freezes the cutoff and reports that it is waiting for unseen data. The same BAT can be run again after candle history grows.

## Preserved state

- GOLD V3 audit-only
- Stage280 exact recovery remains blocked
- Stage307 top candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- shadow disabled
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
