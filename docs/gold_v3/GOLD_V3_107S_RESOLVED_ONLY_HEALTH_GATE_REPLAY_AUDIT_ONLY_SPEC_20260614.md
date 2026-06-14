# GOLD V3 Stage107S Spec — RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY
```

## Why this stage exists

107R6 rebuilt `exit_dt` for the 107Q best-family ledger:

```text
best_family_rows: 5571
best_family_resolved_rows: 5571
best_family_exit_dt_coverage: 1.0
```

107R6 remained blocked because all input sources had broad parity failures outside the 107Q selected ledger. That should not block a resolved-only replay limited to the 107Q best-family ledger, because the selected 5571 rows have full `exit_dt` coverage.

## Important interpretation of `exit_dt`

`exit_dt` is not an entry feature and must not be used as a current-entry condition.

It is only used to decide whether a **past** trade result was already known before the current candidate entry:

```text
past_trade.exit_dt <= current_trade.entry_dt
```

This prevents unresolved/future trade outcomes from entering rolling health history.

## Purpose

Stage107S performs resolved-only health gate replay on:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
```

It compares:

1. base pass-through 107Q best-family ledger
2. resolved-only rolling health gates using only closed past outcomes

## Method

For each current entry sorted by `entry_dt`:

1. Move historical rows into health history only when `exit_dt <= current entry_dt`.
2. Evaluate rolling health policies using historical `result_usd` only.
3. Keep or skip the current row.
4. Do not use the current row result or current exit_dt to decide the current row.

## Policy families tested

```text
pass_through_baseline
candidate_pf_gate
global_side_pf_gate
global_all_pf_gate
```

Default sweep:

```text
window: 20, 50, 100
min_history: 5, 10, 20
pf_threshold: 1.0, 1.15, 1.3, 1.5
```

For `candidate_pf_gate`, history is keyed by `global_candidate_key`.

For `global_side_pf_gate`, history is keyed by `side`.

For `global_all_pf_gate`, history uses all prior resolved selected rows.

## Outputs

```text
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_health_policy_summary.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_best_health_gate_ledger.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_base_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_best_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_best_regime_metrics.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_health_gate_matrix.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_validation_matrix.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_summary.json
FX_OUTPUTS/gold_v3/107sc/GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107sc/paste_me.txt
```

## Gates

Primary gate:

```text
best WR >= base WR
best PF >= base PF
best retention >= 65%
best min_regime_wr >= 60%
best negative_month_count == 0
resolved_only_strict == true
```

Review gate:

```text
best WR gain >= 0.5 percentage point
best PF >= base PF
best retention >= 50%
resolved_only_strict == true
```

If no health gate improves over base, pass-through may remain the best policy, but that is not a live approval.

## Decisions

Allowed decisions:

```text
RESOLVED_ONLY_HEALTH_GATE_PRIMARY_READY_FOR_STAGE108_REVIEW
RESOLVED_ONLY_HEALTH_GATE_REVIEW_READY_FOR_STAGE108_REVIEW
RESOLVED_ONLY_HEALTH_GATE_NO_IMPROVEMENT_KEEP_107Q_BASE_FOR_REVIEW
RESOLVED_ONLY_HEALTH_GATE_BLOCKED_INPUT_INCOMPLETE
```

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
