# GOLD V3 Stage326 — Router State and Latency Robustness Audit

## Purpose

Stage325 found one fixed resolved-only router lead:

`RELATIVE_TRAILING_MEAN_R_N2`

The router uses the last two resolved outcomes from each membership subgroup and takes a candidate only when its subgroup score is at least the other subgroup score.

Stage326 does not search for a new router. It stress-tests this exact fixed policy under operational state and observation assumptions.

## Source integrity

Stage326 requires:

- Stage325 status and decision to match
- selected policy exactly `RELATIVE_TRAILING_MEAN_R_N2`
- selected lane exactly `BALANCED_OR_PREMIUM`
- Stage324 timeline SHA256 to match
- Stage325 selected-trade and decision-trace SHA256 values to match
- baseline selected entries, PnL, R, decisions, reasons, and scores to reproduce within `1e-12`
- no overlapping source positions

## Fixed scenarios

- continuous state, take-all warmup — exact baseline
- annual state reset
- semiannual state reset
- quarterly state reset
- continuous state with warmup skip
- continuous state with one-candidate observation delay
- continuous state with two-candidate observation delay

Every scenario is replayed at:

- recorded 1.0x spread cost
- 1.5x spread cost

No raw feature threshold and no router parameter is retuned.

## Operational gate

The required operational scenarios are:

- annual reset
- semiannual reset
- warmup skip
- one-candidate delay
- two-candidate delay

Each required scenario must satisfy at both 1.0x and 1.5x cost:

- PF at least 1.25
- positive 2024–2025 total R
- DD no more than 3.5R
- both 2024 and 2025 positive

Quarterly reset is a descriptive state-dependence stress and is not required to pass. It intentionally erases more router memory than the audited continuous policy.

## State-dependence classification

Persistent-state dependence is reported when quarterly resets, measured only on 2024–2025, cause either:

- win-rate loss of at least 10 percentage points, or
- DD increase of at least 1R

2026 remains display only and cannot alter the gate or classification.

## Expected operational meaning

If the required scenarios pass but state dependence is detected, the correct interpretation is:

`ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE`

This means the policy remains profitable under moderate restart and latency stresses, but production-equivalent monitoring would need to persist both subgroup histories. Resetting the router every quarter would not reproduce the audited policy.

## Outputs

- `stage326_router_state_and_latency_robustness_audit.json`
- `stage326_router_operational_scenarios.csv`
- `stage326_router_operational_decision_trace.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage325 result unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
