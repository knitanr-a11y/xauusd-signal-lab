# GOLD V3 Stage326A — Router Disagreement Counter Correction Audit

## Purpose

Stage326 completed successfully and its core conclusion remains valid:

`ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE`

However, the two reporting columns that counted take/no-take disagreements against the baseline were incorrect. Every scenario was reported as if every candidate differed from baseline.

Stage326A corrects only those two counters and explicitly confirms that the operational metrics, gate result, state-dependence classification, candidate selection, and contracts are unchanged.

## Root cause

The Stage326 reporting expression used attribute access on the pandas DataFrame column named `take`.

`DataFrame.take` is also a pandas method. Therefore, the comparison referenced the method instead of the `take` column and marked every row as different.

Bracket column access is required:

`frame["take"] != frame["baseline_take"]`

## Integrity checks

Stage326A requires:

- Stage326 status and decision to match
- Stage326 operational gate PASS
- Stage326 state dependence detected
- Stage326 scenario CSV SHA256 to match
- Stage326 decision-trace CSV SHA256 to match
- baseline scenario disagreement counts to recompute to exactly zero
- all non-counter scenario columns to remain byte-equivalent after correction

## Corrected disagreement counts

### 2024–2025

- baseline continuous: 0
- annual reset: 4
- semiannual reset: 6
- quarterly reset: 10
- warmup skip: 4
- one-candidate delay: 3
- two-candidate delay: 6

### 2026 display only

- baseline continuous: 0
- annual reset: 3
- semiannual reset: 3
- quarterly reset: 6
- warmup skip: 0
- one-candidate delay: 1
- two-candidate delay: 2

## Outputs

- `stage326a_router_disagreement_counter_correction_audit.json`
- `stage326a_corrected_router_operational_scenarios.csv`
- `stage326a_corrected_take_disagreement_trace.csv`

## Preserved state

- Stage326 core decision unchanged
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
