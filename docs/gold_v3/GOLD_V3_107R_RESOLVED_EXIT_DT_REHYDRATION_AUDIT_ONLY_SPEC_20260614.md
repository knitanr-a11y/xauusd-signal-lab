# GOLD V3 Stage107R Spec — RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY
```

## Why this stage exists

Stage107Q produced a strong stable-family proxy result:

```text
best_combo_key: F002_L20_T5
best_feature: score
best_op: <=
best_side_scope: ALL
best_family_wr: 63.72%
best_family_pf: 3.129
best_family_retention: 72.98%
best_family_wr_gain: +3.39 percentage points
best_min_regime_wr: 62.86%
primary_gate: true
review_gate: true
```

However, Stage107Q is still not strict live replay because the current ledger lacks `exit_dt`:

```text
resolved_only_strict: false
live_ready: false
```

Strict rolling health/history gates must only use outcomes known before the current entry:

```text
exit_dt <= current entry_dt
```

Stage107R therefore prioritizes `exit_dt` discovery and rehydration before any live-like health gate.

## Purpose

Stage107R searches audit outputs for a trustworthy `exit_dt` source and attempts to attach it to the 107Q best-family ledger.

It must:

1. Read the 107Q best-family trade ledger.
2. Scan `FX_OUTPUTS/gold_v3` CSV headers for exact `exit_dt` sources.
3. Attempt safe joins using high-confidence keys.
4. Produce a resolved best-family ledger if coverage is complete.
5. Block if no exact/full-coverage `exit_dt` source exists.

## Required input

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_summary.json
```

## Source discovery scope

Search only audit-output CSV files under:

```text
FX_OUTPUTS/gold_v3
```

Do not mutate or rewrite source CSVs.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

## Strict source rule

Only an exact column named:

```text
exit_dt
```

can satisfy this stage automatically.

Alias columns such as `close_dt`, `resolved_dt`, `tp_dt`, or `sl_dt` may be cataloged for human review but must not be used as strict `exit_dt` unless a later stage explicitly proves the semantic contract.

## Join priority

Stage107R may attempt these join keys, from strongest to weakest:

```text
global_candidate_key
entry_dt + global_candidate_key
entry_dt + side + candidate_key + profile_id
entry_dt + side + family + condition + profile_id
entry_dt + side + result_usd
```

A join is acceptable only when:

```text
coverage == 100%
non_null_exit_dt == selected_rows
exit_dt >= entry_dt for all selected rows
```

Low-confidence duplicate joins must be reported and blocked unless they satisfy exact 1:1 coverage.

## Outputs

```text
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_exit_dt_source_catalog.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_join_attempts.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_resolved_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_exit_dt_precondition_matrix.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_validation_matrix.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_summary.json
FX_OUTPUTS/gold_v3/107rc/GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107rc/paste_me.txt
```

## Decisions

Allowed decisions:

```text
RESOLVED_EXIT_DT_REHYDRATION_READY_FOR_107S_HEALTH_GATE_REPLAY
RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_EXIT_DT_SOURCE_NOT_FOUND
RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_PARTIAL_OR_AMBIGUOUS_JOIN
RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_INPUT_INCOMPLETE
```

## What this stage must not claim

Stage107R must not claim:

- final live readiness
- health gate success
- MT5/Discord readiness
- final signal readiness
- approval of posthoc seed families

Even if 107R succeeds, the next required stage is a resolved-only rolling health gate replay.
