# GOLD V2 25C92 nearby component oracle boundary audit-only spec

Created: 2026-06-08

Status: `NEARBY_COMPONENT_ORACLE_BOUNDARY_SPEC_READY_AUDIT_ONLY`

## Purpose

25C91 found the best raw-only cluster sweep candidate:

```text
entry_gap=15m
same_count_exact=66/125
source_rule_count_exact=66/125
```

This is not enough to reconstruct CoreB live logic. However, it is high enough to test whether the missing part is primarily:

```text
A. component construction is wrong
B. component-to-top-row association / representative selection is wrong
```

25C92 performs an oracle-style boundary audit: for each top row, search nearby components and check whether any nearby component has the correct `same_count` / `source_rule_count` / `unique_origins` / representative profit.

## Important limitation

This is explicitly not live logic. An oracle that chooses the correct nearby component using the historical answer is not a deployable evaluator.

## Inputs

```text
25c91_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

## Component families

Reuse the 25C91 families:

```text
entry_gap
interval_gap
calendar_bucket
```

Focus gaps:

```text
5, 15, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440, 2880 minutes
```

Nearby windows:

```text
0, 15, 30, 60, 120, 240, 720, 1440 minutes
```

## Outputs

```text
GOLD_V2_25C92_NEARBY_COMPONENT_ORACLE_BOUNDARY_AUDIT_ONLY_REPORT.md
25c92_summary.json
25c92_input_inventory.csv
25c92_nearby_component_oracle_summary.csv
25c92_nearby_component_oracle_rows.csv
25c92_best_candidate_matrix.csv
25c92_decision_matrix.csv
25c92_blocker_matrix.csv
```

## Success interpretation

If all 125 rows have a nearby component with correct count, component construction is probably close and the remaining blocker becomes representative selection / component association.

If not all 125 rows have a nearby correct component, raw-only reconstruction remains insufficient.

Either way, live remains blocked.

## Guardrails

- Oracle matching must not be promoted to live logic.
- No source recovery approval.
- No A002 use.
- No live evaluator/final signal/external actions.
