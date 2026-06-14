# GOLD V3 107K2 result review from generated frontier — audit-only

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Input reviewed from the user-attached generated Stage107K2 artifacts:

```text
gold_v3_107k2_regime_frontier.csv
gold_v3_107k2_all_regime_ledgers.csv
gold_v3_107k2_regime_bin_scores.csv
gold_v3_107h_feature_join_coverage.csv
gold_v3_107h_input_ledger_coverage.csv
gold_v3_107h_ohlc_coverage.csv
```

## Status judgment

```text
GOLD_V3_107K2_DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_READY_WITH_BALANCED_60_AUDIT_ONLY
```

107K2 did not fail as a strategy. It produced a valid regime frontier and then stopped at the final summary writer because of a column name bug:

```text
AttributeError: 'DataFrame' object has no attribute 'unique_trade_days'
expected available column: oos_unique_trade_days
```

The generated frontier is sufficient to decide the next stage.

## Guardrails preserved

- audit_only: true
- live_ready: false
- source_csv_mutated: false
- contract_mutated: false
- manual_candidate_demotion_or_removal: false
- open_asof_allowed: false
- live evaluator / live hook / final signal / MT5 / Discord / AI API: off
- Stage45 runtime / Stage69 runtime / candidate pool: unchanged
- Health gate history remains blocked until `exit_dt` exists and can be enforced by `exit_dt <= current entry_dt`.

## 107K2 aggregate from frontier

```text
regime_frontier_rows: 252
policy_count: 84
regime_count_per_policy: 3
all_regime_pass_65_count: 0
all_regime_pass_60_count: 12
decision: REGIME_BALANCED_60_READY_FOR_REVIEW
next_stage: 107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY
```

Interpretation:

- No policy passed all three regime rows at 65%.
- A balanced 60 policy does exist.
- This is not final/live-ready. It is enough to proceed to regime rehydration and resolved-only health-gate audit.
- The high-vol window `test_end=2027-01-01` is only an upper bound; actual OOS entries end inside the attached data.

## Regime frontier coverage

| regime_split | policy_rows | test_start | test_end_upper_bound | actual_min_oos_entry | actual_max_oos_entry | min_trades | max_trades | pass60_rows | pass65_rows |
|---|---:|---|---|---|---|---:|---:|---:|---:|
| REGIME_2025_H2 | 84 | 2025-07-01 | 2026-01-01 | 2025-07-01 | 2025-12-31 | 394 | 20762 | 53 | 16 |
| REGIME_2026_Q1Q2 | 84 | 2026-01-01 | 2026-05-01 | 2026-01-05 | 2026-04-30 | 60 | 11267 | 23 | 0 |
| REGIME_2026_HIGHVOL_MAYJUN | 84 | 2026-05-01 | 2027-01-01 | 2026-05-01 | 2026-06-12 | 0 | 2189 | 27 | 19 |

## Best balanced-60 policy

```text
best_policy_key: density_safe||100||Q0.6
best_min_wr: 0.601742696053306
best_min_pf: 2.5352617898638443
best_min_trades: 146
best_min_unique_trade_days: 12
best_max_day_trade_share: 0.3287671232876712
best_sum_trades: 8565
best_avg_wr: 0.6181773567575161
balanced_score: 12162.135107375763
```

Per-regime best rows:

| regime_split | actual_oos_entry_range | trades | WR | PF | sum_result_usd | unique_days | max_day_share | pass60 | pass65 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| REGIME_2025_H2 | 2025-07-07 to 2025-12-31 | 5853 | 60.17% | 2.535 | 14857.40 | 95 | 6.37% | true | false |
| REGIME_2026_Q1Q2 | 2026-01-05 to 2026-04-14 | 2566 | 60.21% | 2.556 | 7284.05 | 31 | 9.82% | true | false |
| REGIME_2026_HIGHVOL_MAYJUN | 2026-05-06 to 2026-06-05 | 146 | 65.07% | 2.956 | 604.10 | 12 | 32.88% | true | true |

## Review notes

The best row is balanced enough to continue, but not complete:

- It is a 60-level balanced policy, not a strict 65 policy.
- The weakest WR is only slightly above 60%.
- 2026 high-vol coverage is still short in calendar span and trade count compared with 2025 H2.
- The attached 107K2 ledger has no `exit_dt` column, so rolling health gate must not be run from it directly.
- 2026 Q1Q2 contains weak subperiod behavior in March/April even though the aggregate row passes. 107L should preserve monthly diagnostics.

## 107K2 script fix required

The 107K2 summary aggregation should reference the generated `oos_` columns:

```text
best.oos_unique_trade_days.min()
best.oos_max_day_trade_share.max()
```

instead of:

```text
best.unique_trade_days.min()
best.max_day_trade_share.max()
```

This is an audit-only script fix and does not change source CSVs, candidate pool, runtime signal logic, live evaluator, final signal, Discord, MT5, or AI API.

## Next stage

Create and run:

```text
GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY
```

Required behavior:

1. Read the 107K2 frontier and all-regime ledger.
2. Reconstruct the balanced policy summary from frontier if 107K2 crashed before writing summary CSVs.
3. Rehydrate the best policy ledger by `policy_key` and `regime_split`.
4. Recompute per-regime metrics and verify parity against frontier.
5. Check for `exit_dt`.
6. If `exit_dt` is missing, stop with a blocker and do not simulate rolling health gate.
7. If `exit_dt` exists, run only resolved-only health gate histories where `exit_dt <= current entry_dt`.
