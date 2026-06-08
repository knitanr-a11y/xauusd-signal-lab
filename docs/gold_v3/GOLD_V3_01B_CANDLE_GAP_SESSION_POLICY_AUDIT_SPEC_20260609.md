# GOLD V3 01B candle gap and session policy audit spec

Created: 2026-06-09

Status: `GOLD_V3_01B_CANDLE_GAP_SESSION_POLICY_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 01 normalized the primary GOLD# 2025 candles and passed per-timeframe hard checks, but blocked on strict cross-timeframe open containment:

```text
GOLD_V3_01 status = GOLD_V3_01_CANDLE_TIME_AUDIT_BLOCKED_AUDIT_ONLY
inputs_ok = true
hard_time_ok = true
hard_cross_ok = false
```

01B diagnoses the cross-timeframe mismatches and creates a conservative data-use policy. It does not create features, labels, signals, or live logic.

## Known 01 issues to classify

From 01 cross-timeframe alignment:

```text
M5 not subset of M1: 8 missing M1 open rows
M15 subset of M5: ok
H1 subset of M15: ok
H4 not subset of H1: 236 missing H1 open rows, mostly 00:00 UTC session openings
D1 not subset of H4: 2 warning-level daily/session mismatches
```

## Source inputs

Use only GOLD V3 outputs:

```text
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/gold_v3_01_summary.json
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/gold_v3_01_cross_timeframe_alignment.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/*.csv
```

Required 01 upstream status:

```text
GOLD_V3_01_CANDLE_TIME_AUDIT_BLOCKED_AUDIT_ONLY
```

## Diagnostic checks

For each pair:

```text
M5/M1
M15/M5
H1/M15
H4/H1
D1/H4
```

Compute:

```text
child_open_count
missing_parent_open_count
missing_parent_open_ratio
sample_missing_times
parent_rows_inside_child_bar_min/max/mean
missing_parent_open_but_child_native_exists
```

For M5/M1, additionally mark affected M5 bars and propose a label guard:

```text
m1_label_guard_required = true if missing M1 rows exist inside or at child bar open
```

For H4/H1 and D1/H4, classify as native-HTF session mismatch rather than a hard blocker when:

```text
native child timeframe OHLC passed 01 hard checks
missing parent opens are session-boundary style gaps
V3 will use native HTF asof bars, not reconstruct H4 from H1 or D1 from H4
```

## Policy outputs

Create a policy matrix with:

```text
component
policy_name
allowed
severity
reason
next_step_requirement
```

Expected policy direction:

```text
native_m1/m5/m15/h1/h4/d1_candles_allowed = true
reconstruct_h4_from_h1_allowed = false
reconstruct_d1_from_h4_allowed = false
m1_intrabar_label_allowed = conditional, with gap guard
m5_intrabar_label_allowed = true if M5 native row exists
htf_feature_join_allowed = true only as native closed/asof HTF bars
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/01b_candle_gap_session_policy_audit/
```

Output files:

```text
GOLD_V3_01B_CANDLE_GAP_SESSION_POLICY_AUDIT_REPORT.md
gold_v3_01b_summary.json
gold_v3_01b_input_inventory.csv
gold_v3_01b_pair_gap_diagnostics.csv
gold_v3_01b_missing_open_detail.csv
gold_v3_01b_data_use_policy_matrix.csv
gold_v3_01b_decision_matrix.csv
gold_v3_01b_blocker_matrix.csv
```

## Status names

If 01 inputs are missing or upstream status differs:

```text
GOLD_V3_01B_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If native candles are usable but M1/H4/D1 reconstruction limitations must be recorded:

```text
GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY
```

If major lower-timeframe gaps prevent even native entry/label policy:

```text
GOLD_V3_01B_CANDLE_GAP_POLICY_BLOCKED_AUDIT_ONLY
```

## Guardrails

- GOLD V3 only.
- Do not read or reuse GOLD V2 selected/source/final/arbitration artifacts.
- No features, no labels, no candidate exploration, no signals.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- NO_SIGNAL must not notify Discord.
