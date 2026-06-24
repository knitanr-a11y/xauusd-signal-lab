# GOLD V3 Stage327 — Persistent Router State Checkpoint/Restart Parity Audit

## Purpose

Stage326A corrected the Stage326 disagreement counters and confirmed that the Stage326 core decision remains unchanged:

`ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE`

Stage327 verifies that the fixed Stage325 router can be stopped and restarted without changing any decision or selected trade when its minimal state is serialized and restored correctly.

## Fixed router

- lane: `BALANCED_OR_PREMIUM`
- policy: `RELATIVE_TRAILING_MEAN_R_N2`
- warmup: take all until both groups have two resolved observations
- outcome history: every resolved source candidate updates its group history, including skipped candidates
- no policy retuning
- no new raw feature threshold

## Minimal persistent state

The state schema stores:

- schema version
- policy and selected lane
- cost view
- processed candidate count
- last processed entry and exit timestamps
- for `PREMIUM_INVOLVED`:
  - total resolved count
  - last two resolved R values
- for `BALANCED_WITHOUT_PREMIUM`:
  - total resolved count
  - last two resolved R values

The full historical list is not required because the fixed N2 policy uses only the last two R values. Total resolved counts are retained to reproduce warmup state and exact trace counts.

## Integrity chain

Stage327 requires:

- Stage326A status and decision to match
- Stage326A confirmation that the operational gate passed
- Stage326A confirmation that state dependence was detected
- Stage326 JSON SHA256 to match Stage326A
- Stage324 timeline, Stage325 selected trades, and Stage325 trace SHA256 values to match Stage326
- Stage325 selected-trade and decision-trace parity at `1e-12`
- non-overlapping source trades

## Restart schedules

Both recorded 1.0x and stressed 1.5x cost views are tested under:

- one restart after every possible individual candidate position
- repeated restart after every 1, 2, 3, 5, and 8 candidates
- restart at every year boundary
- restart at every half-year boundary
- restart at every quarter boundary

These are state-preserving restarts. They do not reset the subgroup histories.

## Required parity

Every schedule must reproduce the uninterrupted baseline exactly for:

- take/no-take decision
- decision reason
- subgroup history counts
- subgroup scores within `1e-12`
- selected trade keys
- selected PnL within `1e-12`
- selected R within `1e-12`
- terminal serialized state

## Expected decision

When all schedules pass:

`PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_CONFIRMED`

This confirms serialization and restart equivalence only. It is not a production promotion.

## Outputs

- `stage327_persistent_router_state_checkpoint_restart_parity_audit.json`
- `stage327_router_restart_checkpoint_summary.csv`
- `stage327_router_state_snapshots.csv`
- `stage327_router_terminal_state_snapshot.json`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage326 core decision unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
