# GOLD CHALLENGER C1 V2 DATA V3 — Formal Research Audit

Date: 2026-08-01  
Candidate: `GOLD_CHALLENGER_C1_V2_DATA_V3`  
Formal status: **`RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_FAILED`**

## Executive conclusion

The original `(2)` inputs are unavailable. The earlier 123-trade/PF1.947 result remains `UNEXPECTED_DISCOVERY_DIAGNOSTIC` and was not used as a reproduction target.

A separate `(3)`-source candidate was preregistered and rebuilt from frozen source hashes. Its E40 router, V17 wave grammar, candidate generation, exact-M1 execution, one-position accounting, and V19-priority accounting were separated into ordinary UTF-8 Python modules. The fixed candidate produced 188 raw event onsets, 125 accepted observations, and 124 resolved observations. One accepted observation remained unresolved because the raw M1 horizon contained unexpected missing-minute gaps; it is excluded from resolved-only performance.

The candidate passed most preregistered robustness gates, including both directions, additional cost, month-block bootstrap, matched random controls, pseudo-wave controls, all leave-one-scale-out variants, and dual exact-M1 execution. It nevertheless **failed the complete formal contract** because the combined PF degradation relative to frozen V19 exceeded the preregistered maximum by a small amount. No rescue, threshold adjustment, state deletion, direction deletion, or policy change was made.

This is not deployable, validated, Shadow-ready, or authorized for Discord/AI/MT5 use.

## Phase 0 and source authority

- `(2)` input availability: **No**
- New authority: frozen `(3)` source manifest
- Old 123 result: diagnostic only
- V19 running environment: untouched
- GitHub writes during Phase 0: none
- Candidate/runtime implementation during Phase 0: none

`goldsharp_m15(3).csv` was unavailable. An initial sharp-M1-only derivation failed closed because the first partial 15-minute bucket began at 01:08 and conflicted with the existing old M15 bucket. The failure was retained. Before result calculation, the authoritative rule was corrected to aggregate the complete validated old+sharp M1 union. The final derived M15 SHA256 is:

`544aea77562b1448cd21b368cdf55f2c34935e445fc6855c4226bb6c27a5f41f`

It matches all 81,781 existing old `(3)` broker M15 rows exactly.

## Upstream reference difference

The first difference from the old V10 `(2)` reference is not repaired:

- timestamp: `2024-07-02 01:15:00`
- classification: `DATA_VERSION_MISMATCH`
- merge status: `right_only`
- reference chosen side: `None`
- DATA_V3 chosen side: `SHORT`
- DATA_V3 LONG rank: `0.008566533409480296`
- DATA_V3 SHORT rank: `0.251284980011422`
- DATA_V3 P90: `False`
- entry M1 index: `530301`

Classification is `DATA_VERSION_MISMATCH`, not an implementation rescue target.

## Fixed candidate result — resolved only

| Scope | Trades | Wins | Losses | PF | Net | EV | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Challenger | 124 | 64 | 60 | 1.913512 | +535.19 | +4.3160 | 80.00 |
| Frozen V19 | 169 | 93 | 76 | 2.029956 | +730.96 | +4.3252 | 80.00 |
| V19-priority combined | 293 | 157 | 136 | 1.977299 | +1266.15 | +4.3213 | 60.22 |

Monthly resolved-PnL correlation between V19 and Challenger: `0.000310966`.

## Forward periods

| Period | Trades | PF | Net | Max DD |
|---|---:|---:|---:|---:|
| 2024H2 | 19 | 1.235134 | +21.63 | 30.00 |
| 2025H1 | 40 | 1.651411 | +133.65 | 70.00 |
| 2025H2 | 26 | 3.253777 | +199.91 | 30.00 |
| 2026H1 | 32 | 2.266667 | +190.00 | 30.00 |
| 2026JUL | 7 | 0.800000 | -10.00 | 50.00 |

Four of five fixed forward periods were positive. 2026JUL remains negative; no month rescue was applied.

## Direction and cost

| Slice | Trades | PF | Net | Max DD |
|---|---:|---:|---:|---:|
| LONG | 72 | 2.017584 | +331.59 | 49.58 |
| SHORT | 52 | 1.783077 | +203.60 | 63.40 |
| Additional cost +0.30/trade | 124 | 1.824678 | +497.99 | 82.40 |
| Additional cost +0.60/trade | 124 | 1.740927 | +460.79 | 84.80 |

Both directions are retained.

## Statistical and structural controls

### Month-block bootstrap

- iterations: 2000
- months: 25
- probability net > 0: 1.0000
- 5th percentile net: +286.20
- 5th percentile PF: 1.434369

### Matched random control

The control samples equal accepted counts by entry month and chosen direction from all causal sub-P90 wave-transition onsets, then applies identical M1 execution and V19 priority.

- iterations: 2000
- control pool resolved trades: 1145
- actual net percentile: 1.0000
- actual PF percentile: 0.9985

### Pseudo wave-state control

- iterations: 2000
- actual net percentile: 1.0000
- actual PF percentile: 1.0000
- median pseudo trade count: 143.0

### Leave-one-wave-scale-out

All six preregistered omissions remained PF > 1. The weakest was H1_K080 omitted: PF 1.263811, net +217.04. This is recorded as a pass, not a reason to remove or favor a scale.

### Wave / E40 / interaction

| Component | Trades | PF | Net | Max DD |
|---|---:|---:|---:|---:|
| Wave-only | 137 | 1.701936 | +481.43 | 93.68 |
| E40-only | 754 | 0.975111 | -107.05 | 618.20 |
| Fixed interaction | 124 | 1.913512 | +535.19 | 80.00 |

This is mechanism evidence only. It does not authorize redesign.

## Rank-band mechanism diagnostic

| Rank band | Trades | PF | Net |
|---|---:|---:|---:|
| <0.50 | 30 | 1.079263 | +15.06 |
| 0.50–0.70 | 40 | 2.087172 | +191.19 |
| 0.70–0.80 | 28 | 1.380000 | +60.80 |
| 0.80–0.90 | 26 | 5.469000 | +268.14 |

These bands are diagnostic. The threshold remains `< P90`; no band selection is permitted.

## V19 interaction and preemption

- raw Challenger onsets: 188
- exact same-timestamp V19 entries: 0
- onsets inside an open V19 position: 1 (0.5319%)
- accepted Challenger observations: 125
- resolved Challenger observations added to portfolio: 124
- Challenger preemptions at actual V19 arrival: 2
- suppressed Challenger onsets while another position was open: 63

| Fixed comparison | Trades | PF | Net | Max DD |
|---|---:|---:|---:|---:|
| Main V19-priority/preempt policy | 293 | 1.977299 | +1266.15 | 60.22 |
| Preregistered no-preempt counterfactual | 291 | 1.987204 | +1272.15 | 63.42 |

The main policy remains fixed. The counterfactual cannot be selected after seeing results.

## Exact-M1 independent recalculation

For all 188 raw candidate onsets, the indexed/Numba implementation and the simple one-trade-at-a-time implementation matched exactly on:

- entry index
- exit index
- exit reason
- PnL

Frozen V19 was independently recalculated on DATA_V3 M1 and matched all 169 trades on PnL and exit timestamp.

## Formal gates

| Gate | Result |
|---|---|
| `minimum_resolved_trades` | PASS |
| `pooled_pf` | PASS |
| `pooled_net_positive` | PASS |
| `positive_forward_periods` | PASS |
| `long_pf` | PASS |
| `short_pf` | PASS |
| `direction_counts` | PASS |
| `cost_060_pf` | PASS |
| `bootstrap` | PASS |
| `matched_random` | PASS |
| `pseudo_wave` | PASS |
| `leave_one_scale_out` | PASS |
| `combined_pf_degradation` | FAIL |
| `combined_dd_increase` | PASS |
| `dual_execution` | PASS |


### Formal failure reason

The sole failed gate is `combined_pf_degradation`.

- frozen V19 PF: `2.029956319572`
- preregistered minimum combined PF: `V19 PF - 0.05 = 1.979956319572`
- observed combined PF: `1.977299391769`
- shortfall below the gate: `0.002656927803`

Although the miss is numerically small, the gate was frozen before results. It is therefore a formal failure. The threshold is not relaxed and the candidate is not rescued.

## Accounting report correction

A final report review found two presentation/accounting-order issues that did not alter entries or per-trade PnL:

1. preliminary monthly correlation included one unresolved observation as a zero monthly sum;
2. preliminary no-preempt DD summarized concatenated system rows before exit-time sorting.

The corrected resolved-only correlation is `0.000310966` and corrected no-preempt DD is `63.42`. The formal pass/fail result did not change. Details are in `outputs/accounting_report_correction.json`.

## Final classification and prohibitions

Formal classification:

`RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_FAILED`

Therefore:

- do not call this validated, deployable, or live-ready;
- do not implement or start a Shadow;
- do not add Discord, AI, local state, BAT loops, live CSV monitoring, or MT5 orders;
- do not adjust state, rank threshold, direction, TP/SL, months, or V19 priority to rescue the result;
- require a newly accumulated future period and a separately authorized protocol before any reconsideration.

V19 remains fully frozen and unchanged.

## Reproduction commands

```bat
python -m compileall scripts/gold_challenger_c1
python -m pytest -q tests/gold_challenger_c1
python -m gold_challenger_c1.run_reproduction
python -m gold_challenger_c1.robustness_audit
```

Run with the package `scripts` directory on `PYTHONPATH` and with the source files matching `config/source_manifest.json`.
