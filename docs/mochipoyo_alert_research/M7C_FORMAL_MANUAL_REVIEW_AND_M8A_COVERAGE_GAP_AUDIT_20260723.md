# MOCHIPOYO Alert Research — M7C Formal Manual Review / M8A Coverage Gap Audit

## 1. Scope

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`  
Formal pre-M8A baseline commit: `c0bd4b9d20235422720b7c250e95a2e2c3f64b4d`

This review uses the user-supplied M7C formal-gate snapshot built at `2026-07-23T13:06:15Z`.

The M7C prospective start remains fixed at:

`2026-07-20T14:54:15Z`

No M7C kernel, threshold, grace period, matching rule, runtime manifest, prospective start, review gate, Discord setting, MT5 setting, live-ready setting, final-signal setting, or entry gate is changed by this review.

No exact proprietary Mochipoyo formula reproduction is claimed.

## 2. Formal gate result

The frozen report reached all formal review requirements:

- supported source events: 35 / minimum 30
- BTCUSD supported: 19 / minimum 10
- XAUUSD supported: 16 / minimum 10
- PRIMARY_LONG: 12 / minimum 5
- PRIMARY_SHORT: 5 / minimum 5
- LONG_EXIT: 13
- SHORT_EXIT: 5
- total exits: 18 / minimum 10
- formal review state: `READY_FOR_MANUAL_REPRODUCTION_REVIEW`

The frozen supported-source reproduction result is:

- exact match: 19 / 35 = 54.2857%
- within one M15 bar: 21 / 35 = 60.0%
- missed: 14 / 35 = 40.0%
- wrong transition nearby: 0
- unsupported REENTRY: 10, kept separate and not scored

Extra proxy state at freeze:

- finalized extra proxy signals: 36
- pending source-arrival grace: 2

The two pending-grace rows are not promoted to `EXTRA_CANDIDATE` for M8B. They remain pending and are excluded from outcome evaluation until finalized.

## 3. Frozen M7C input hashes

The formal-gate attachment set was copied before M8A code/formula work and identified by SHA256:

- `latest_m7c_prospective_shadow.json`: `885b54e02a239ec0efcc2130208d8a609202aa0ecb195a7a3176c13449037070`
- `latest_m7c_shadow_loop_status.json`: `9e6b4ec2a5718fdf8be5d1ed2dde90d8bc7752362b67e8bee4327ee031056dc2`
- `latest_m7c_source_event_comparisons.csv`: `6a913d32f8883767d7ee794b20767ca1d3518ec6a302682a374eca1494202eea`
- `latest_m7c_extra_proxy_signals.csv`: `ecdc409d6ea66e40f89dc6e606b0d7b4a85840b5798958171abb4766bb0de189`
- `latest_m7c_proxy_signals.csv`: `8a53488bddde84d7560a983ad07a7992e1210da73a7507a3ec9b35c4521c8d6d`
- `latest_m7c_proxy_decisions.csv`: `a2cf88d7da6c00a179c9a6ddb443ab2289022b8bd13b279a457a8375f613e055`
- `m7c_shadow_forever.log`: `08cb551fbc51b86a4c00d9ab5edd01c46bea0bbf30b2f0e095f207bf986447d9`

Frozen ZIP SHA256:

`f61f5de930d5034b8b5cebc3edc759e7edeaac32a999a837d9f62c07809ce66d`

## 4. M8A method

M8A is a pre-decision-only coverage-gap audit.

It does not use:

- future bars
- future high/low/close
- MFE / MAE
- TP / SL result
- win/loss
- PF
- future trade outcome
- historical refit

For each `MISSED` supported source event, the frozen proxy decision row at the same M15 decision boundary is inspected.

A miss is first separated into:

1. direct frozen-kernel gap while proxy state is eligible; or
2. state divergence where the proxy is in a different state from the source state machine.

For state divergence, the audit tracks the most recent timestamp at which source and proxy states diverged. This is descriptive causal-state bookkeeping only; it does not use future outcomes.

## 5. M8A result

M8A status: `PASS`

Normalized records:

- `SOURCE_MATCHED`: 21
  - EXACT_MATCH: 19
  - LATE_1_BAR: 2
- `MISSED_SOURCE`: 14
- unsupported REENTRY: 10
- `EXTRA_CANDIDATE`: 36 finalized extra proxy signals
- pending source-arrival grace: 2, excluded from M8B

### 5.1 Missed-source gap classes

The 14 misses split cleanly into three groups:

#### A. DIRECT_EXIT_THRESHOLD_GAP — 5

Raw alert IDs:

- 80 XAUUSD LONG_EXIT
- 85 BTCUSD LONG_EXIT
- 91 XAUUSD LONG_EXIT
- 97 BTCUSD SHORT_EXIT
- 99 XAUUSD LONG_EXIT

At these source decision boundaries the proxy state was eligible, but the frozen exit RCI threshold was not met.

Breakdown:

- LONG_EXIT: 4
- SHORT_EXIT: 1

#### B. STATE_DIVERGENCE_AFTER_PRIOR_MISSED_SOURCE — 6

Raw alert IDs:

- 82 XAUUSD PRIMARY_LONG — divergence traced to missed source 80 LONG_EXIT
- 86 BTCUSD PRIMARY_SHORT — divergence traced to missed source 85 LONG_EXIT
- 88 BTCUSD SHORT_EXIT — divergence traced to missed source 85 LONG_EXIT
- 98 BTCUSD PRIMARY_LONG — divergence traced to missed source 97 SHORT_EXIT
- 100 BTCUSD LONG_EXIT — divergence traced to missed source 97 SHORT_EXIT
- 101 XAUUSD PRIMARY_SHORT — divergence traced to missed source 99 LONG_EXIT

These are cascade misses: a prior source state change was not reproduced, so later source transitions were evaluated while the proxy remained in a different state.

#### C. STATE_DIVERGENCE_AFTER_PRIOR_EXTRA_PROXY — 3

Raw alert IDs:

- 67 BTCUSD PRIMARY_LONG
- 77 BTCUSD PRIMARY_LONG
- 104 BTCUSD PRIMARY_SHORT

At each of these source times the proxy state was already occupied by an earlier unmatched extra proxy transition.

### 5.2 Important interpretation

Among all 14 missed source events:

- direct PRIMARY kernel gap while the required proxy state was correct: **0**
- direct exit-threshold gap: **5**
- state-divergence/cascade gap: **9**

Therefore the current frozen sample does **not** support the claim that the primary RCI-turn + EMA-stack conditions themselves are the direct dominant cause of missed PRIMARY alerts.

The larger observed coverage issue is state-machine divergence, originating from:

- exit thresholds that fail to reproduce a source exit, then cascade into later misses; and
- extra proxy entries that occupy the proxy state before a later source primary alert.

This is a diagnostic result only. M8A does not authorize changing exit thresholds, suppressing extras, or changing state-machine rules.

## 6. Collector incident disposition

The two observed collector HTTP 500 / Worker 1101 failures were transient. The cursor was preserved across failure and subsequent collection resumed from the preserved cursor. No evidence of cursor skipping was found in the supplied collector evidence.

This does not change the frozen M7C prospective start or formal sample validity.

## 7. Decision

M7C manual review: complete.  
M8A coverage-gap audit: complete / PASS.

No exact proprietary-formula reproduction claim is made.

Next stage:

`M8B_EXTRA_SIGNAL_OUTCOME_AUDIT`

M8B must evaluate only the 36 finalized `EXTRA_CANDIDATE` timestamps frozen by M8A. The two pending-grace rows are excluded until they become finalized.

M8B must keep source-matched Mochipoyo alerts outside any extra-loss suppression gate by default.

M8B future outcomes must be evaluated separately from candidate creation and must obey the existing live-causal/no-lookahead contracts and explicit cost assumptions. No M8B outcome rule is inferred or tuned from future data before its evaluation contract is frozen.
