# GOLD V2 25C87 condition object and time alignment replay audit-only spec

Created: 2026-06-08

Status: `CONDITION_OBJECT_AND_TIME_ALIGNMENT_REPLAY_SPEC_READY_AUDIT_ONLY`

## Purpose

25C86 tested `same_count` as the number of fully-passing frozen rules. That did not match CoreB top 125.

25C87 tests the next likely semantics:

```text
same_count = number of individual same-count condition objects that pass
```

It also tests feature snapshot time alignment offsets, because 25C86 joined only 109/125 top rows to feature snapshot times.

## Inputs

Resolve locally:

```text
25c86_summary.json
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
gold_v2_coreb_combined_required_feature_snapshot.csv
gold_v2_coreb_combined_selected_conditions.csv
gold_v2_coreb_combined_same_count_conditions.csv
frozen_coreB_rr125_source_rule_conditions_20260603.json
frozen_coreB_same_count_source_universe_20260604.json
```

## Replay families

For each feature row:

```text
selected_csv_condition_hit_count
same_count_csv_condition_hit_count
selected_json_condition_hit_count
same_count_json_condition_hit_count
```

For CoreB top 125 rows, test feature alignment offsets:

```text
-1440, -720, -240, -120, -60, -30, -15, 0, +15, +30, +60, +120, +240, +720, +1440 minutes
```

Compare each predicted condition-hit count against:

```text
top.same_count
top.source_rule_count
```

## Success definition

A candidate is meaningful only if either:

```text
all 125 rows match exactly
```

or, if pre-feature-snapshot rows are missing:

```text
all feature-overlap rows match exactly and missing rows are explained by feature time coverage
```

Even then, it is not live-approved. It must be marked human review required.

## Guardrails

- A002 is not used.
- No source recovery approval.
- No live evaluator enablement.
- No Discord/MT5/AI/live/final actions.
