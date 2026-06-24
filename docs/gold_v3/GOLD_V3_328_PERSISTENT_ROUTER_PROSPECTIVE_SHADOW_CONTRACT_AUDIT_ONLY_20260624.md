# GOLD V3 Stage328 — Persistent Router Prospective Shadow Contract

## Purpose

Stage327 confirmed exact checkpoint/restart parity for the fixed router:

- lane: `BALANCED_OR_PREMIUM`
- policy: `RELATIVE_TRAILING_MEAN_R_N2`
- cost view: recorded 1.0x spread-adjusted R

Stage328 freezes the future-only audit contract and the immutable bootstrap state that a later prospective shadow runner must copy before processing its first post-freeze candidate.

## Existing cutoff reused

Stage328 does not create or move a new market-data cutoff. It reuses the already frozen Stage319 cutoff:

- prospective candidate `decision_dt` must be strictly greater than the Stage319 frozen latest closed M5 close time
- the Stage319 contract itself remains unchanged and frozen
- the Stage314 contract remains unchanged and active

## Exact prospective candidate lane

The source candidate remains:

`M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`

Membership is fixed as follows.

### Balanced

`CONSENSUS_OR_ATR_STEADY_AND_RANGE`

Equivalent expression:

- `pooled_track_count >= 2`, or
- `1.10 <= atr_ratio_signal <= 1.45` and `0.70 <= range_atr_signal <= 1.05`

### Premium

`TREND_FLOW_COMPRESSION_GE_0_95`

Equivalent expression:

- `compression_ratio_signal >= 0.95`

### Router group assignment

- Premium membership has precedence and becomes `PREMIUM_INVOLVED`
- otherwise a Balanced member becomes `BALANCED_WITHOUT_PREMIUM`

## Frozen bootstrap state

The Stage327 1.0x terminal state is validated against all 37 Stage324 candidates and frozen unchanged.

The bootstrap stores:

- processed candidate count
- last processed entry and exit timestamps
- Premium resolved count and last two R values
- Balanced-without-Premium resolved count and last two R values

The bootstrap file is immutable. A later runtime must copy it to a separate mutable state file before processing future candidates.

## State update rules

- update only after a source candidate resolves
- skipped candidates still update their subgroup history after resolution
- pending candidates have no as-of PnL and do not update state
- state resets are forbidden
- processing is append-only
- no automatic rule change
- no automatic promotion

## Initial state interpretation

At freeze time, both groups have completed warmup.

The first post-freeze candidate is routed immediately from the persisted scores rather than by take-all warmup.

## Outputs

- `stage328_persistent_router_prospective_shadow_contract.json`
- `stage328_persistent_router_bootstrap_state.json`
- `stage328_persistent_router_prospective_shadow_watch.json`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
