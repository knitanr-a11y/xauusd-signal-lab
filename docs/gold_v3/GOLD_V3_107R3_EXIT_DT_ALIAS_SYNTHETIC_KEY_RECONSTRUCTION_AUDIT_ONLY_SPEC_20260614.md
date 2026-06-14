# GOLD V3 Stage107R3 Spec — EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY
```

## Why this stage exists

Stage107R2 proved that exact `exit_dt` sources exist and share columns with the 107Q best-family ledger, but no strict join passed:

```text
exact_exit_dt_source_count: 19
shared_column_source_count: 19
candidate_key_diagnostic_rows: 189
strict_join_pass_count: 0
resolved_rows: 0
decision: EXIT_DT_SOURCE_INTELLIGENCE_RECONSTRUCTION_PLAN_READY
```

The best diagnostics were only `entry_dt` joins, which are not unique enough:

```text
selected_rows: 5571
selected_unique_keys(entry_dt): 453
selected_duplicate_keys(entry_dt): 5118
coverage: about 11.34%
strict_join_pass: false
```

Stage107R3 attempts a safer reconstruction path before asking for a new resolved source ledger.

## Purpose

Stage107R3 attempts alias-aware and synthetic-key `exit_dt` reconstruction.

It must:

1. Read the 107Q best-family ledger.
2. Read the 107R2 exact `exit_dt` source detail.
3. Normalize known column aliases, such as `direction` -> `side` and `profile` -> `profile_id`.
4. Build synthetic key candidates from normalized common columns.
5. Attempt strict full-coverage joins.
6. If no strict join passes, produce a precise source-contract requirement for generating a resolved ledger.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_exact_exit_dt_source_detail.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107r2c/gold_v3_107r2_candidate_key_diagnostics.csv
```

## Alias map

The stage may use column aliases only for matching columns, not for inventing results.

Examples:

```text
side: side, direction, trade_side, candidate_side, signal_side, portfolio_side
profile_id: profile_id, profile, tp_sl_profile, tp_sl_profile_id, risk_profile
family: family, rule_family, candidate_family
condition: condition, rule_condition, candidate_condition
candidate_key: candidate_key, rule_key, strategy_key, global_candidate_key
result_usd: result_usd, pnl_usd, profit_usd, net_usd
score: score, ledger_score, feature_score
```

## Strict acceptance rule

A reconstructed ledger is accepted only if:

```text
coverage == 100%
non_null_exit_dt == selected_rows
exit_dt >= entry_dt for all rows
source duplicate key count == 0
```

If these conditions are not met, the stage must not write a final resolved ledger as ready.

## Outputs

```text
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_alias_source_column_map.csv
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_synthetic_key_join_attempts.csv
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_resolved_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_resolved_ledger_contract_requirement.csv
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_validation_matrix.csv
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_summary.json
FX_OUTPUTS/gold_v3/107r3c/GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107r3c/paste_me.txt
```

## Decisions

Allowed decisions:

```text
EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_READY_FOR_107S
EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_NEED_RESOLVED_SOURCE_LEDGER
EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_INPUT_INCOMPLETE
```

## If blocked

If blocked, the required resolved source ledger contract is:

```text
entry_dt
exit_dt
side
result_usd
profile_id
candidate_key or global_candidate_key
family
condition
source_name
```

The resolved ledger must be produced by the same TP/SL outcome resolution process that created the final `result_usd`, not by manual post-hoc approximation.

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
