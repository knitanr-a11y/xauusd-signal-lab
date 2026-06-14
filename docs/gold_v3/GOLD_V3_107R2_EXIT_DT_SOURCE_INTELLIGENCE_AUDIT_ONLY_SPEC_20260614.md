# GOLD V3 Stage107R2 Spec — EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY
```

## Why this stage exists

Stage107R found exact `exit_dt` sources but could not join them:

```text
exact_exit_dt_source_count: 19
join_attempt_rows: 0
resolved_rows: 0
decision: RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_PARTIAL_OR_AMBIGUOUS_JOIN
```

This means the blocker is not simply “no exit_dt exists”. The blocker is that the exact `exit_dt` sources did not expose the currently expected join key sets, or the join intelligence did not inspect them deeply enough.

Stage107R2 must catalog the 19 exact `exit_dt` sources in detail and produce the next safe join/reconstruction plan.

## Purpose

Stage107R2 performs source intelligence, not final joining.

It must:

1. Read 107R exit_dt source catalog.
2. Inspect every exact `exit_dt` source header and row count.
3. Compare each source header against the 107Q best-family ledger header.
4. Report shared key columns, missing key columns, duplicate risk, and candidate join families.
5. Attempt safe diagnostics on individual columns and candidate key subsets.
6. Produce a recommended next action.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_exit_dt_source_catalog.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_join_attempts.csv
```

## Strict safety rules

This stage is audit-only and must not mutate:

- source CSVs
- CSV contract
- candidate pool
- runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5
- AI API

This stage must not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

## Join acceptance rule

Stage107R2 may report candidate joins, but it must not claim resolved readiness unless a join satisfies:

```text
coverage == 100%
non_null_exit_dt == selected_rows
exit_dt >= entry_dt for all rows
source duplicate key count == 0
```

If no strict join passes, the stage must remain blocked and provide a concrete next-stage plan.

## Outputs

```text
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_exact_exit_dt_source_detail.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_shared_column_matrix.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_candidate_key_diagnostics.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_recommended_next_action.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_validation_matrix.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_summary.json
FX_OUTPUTS/gold_v3/107r2c/GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107r2c/paste_me.txt
```

## Decisions

Allowed decisions:

```text
EXIT_DT_SOURCE_INTELLIGENCE_STRICT_JOIN_READY_FOR_107S
EXIT_DT_SOURCE_INTELLIGENCE_RECONSTRUCTION_PLAN_READY
EXIT_DT_SOURCE_INTELLIGENCE_SOURCE_CONTRACT_REVIEW_REQUIRED
EXIT_DT_SOURCE_INTELLIGENCE_BLOCKED_INPUT_INCOMPLETE
```

## Expected next stage

If strict join still fails but a valid source with enough overlapping columns exists, next stage should be:

```text
107R3_EXIT_DT_RECONSTRUCTION_FROM_LEDGER_SOURCE_AUDIT_ONLY
```

If no usable exact `exit_dt` source exists, the next step is not another filter search; it is to generate or expose a resolved trade ledger containing `entry_dt`, selected candidate keys, result, and `exit_dt` from the original TP/SL resolution process.
