# GOLD V2 25C89 CoreB direct SOT parity package audit-only report

Created UTC: 2026-06-08T09:25:18.501493+00:00

Status: `COREB_DIRECT_SOT_PARITY_PACKAGE_READY_AUDIT_ONLY_LIVE_REPLAY_BLOCKED`

## Purpose

Create a clean CoreB-only package after demoting A002. CoreB performance is now evaluated from the direct 13C selected top-ledger 125-row historical SOT, not from A002.

No source recovery, live evaluator, final signal, Discord, MT5, AI, or live hook is enabled.

## Final decision

```text
A002 = auxiliary evidence only
CoreB main historical source = gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
CoreB direct condition in top ledger = policy=RR125_from_RR1_rules AND filter=same_count>=15
CoreB historical SOT metrics = READY
CoreB future/live OHLC replay = BLOCKED until cluster representative logic is recovered
```

## CoreB direct SOT metrics

| scope | dataset | profit_column | count | wins | losses | breakeven | win_rate | pf | gross_win | gross_loss | total_r | avg_r | worst_r | best_r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CoreB_13C_selected_top_ledgers | 2025 | profit | 104 | 75 | 29 | 0 | 0.721154 | 3.44351 | 201.547 | 58.5295 | 143.017 | 1.37517 | -3 | 3.75 |
| CoreB_13C_selected_top_ledgers | 2026 | profit | 21 | 17 | 4 | 0 | 0.809524 | 5.15385 | 50.25 | 9.75 | 40.5 | 1.92857 | -3 | 3.75 |
| CoreB_13C_selected_top_ledgers | total | profit | 125 | 92 | 33 | 0 | 0.736 | 3.68774 | 251.797 | 68.2795 | 183.517 | 1.46814 | -3 | 3.75 |

## Direct SOT parity checks

| check_id | check | observed | expected | status | detail |
| --- | --- | --- | --- | --- | --- |
| C89-P001 | selected_top_ledgers_rows | 125 | 125 | PASS | gold_v2_13c_coreb_rr125_selected_top_ledgers.csv row count |
| C89-P002 | top_ledger_rr125_same_count15_rows | 125 | 125 | PASS | rr125_top_ledgers filtered by policy=RR125_from_RR1_rules and filter=same_count>=15 |
| C89-P003 | selected_equals_filtered_top_ledger | 0 | 0 | PASS | full-row set diff between selected SOT and top-ledger filtered target |
| C89-P004 | all_direction_buy | 125 | 125 | PASS | CoreB direct SOT BUY-only |
| C89-P005 | rr_bucket_all_rr125 | 125 | 125 | PASS | CoreB direct SOT RR bucket |
| C89-P006 | same_count_min15 | 125 | 125 | PASS | CoreB direct SOT same_count filter |
| C89-P007 | dataset_2025_count | 104 | 104 | PASS | 13C CoreB 2025 count |
| C89-P008 | dataset_2026_count | 21 | 21 | PASS | 13C CoreB 2026 count |

## Final SOT join parity

| check_id | check | observed | expected | status | detail |
| --- | --- | --- | --- | --- | --- |
| C89-F001 | selected_rows_in_13c_final_sot_by_coreb_cluster_profit | 125 | 125 | PASS | selected top-ledger rows present in gold_v2_13c_coreb_final_sot_rows by dataset+entry_time+coreb_cluster_id+coreb_profit_r |
| C89-F002 | 13c_final_sot_rows_in_selected_by_coreb_cluster_profit | 125 | 125 | PASS | gold_v2_13c_coreb_final_sot_rows matches selected rows by CoreB-specific key |
| C89-F003 | selected_rows_in_final_portfolio_coreb_rows_by_coreb_cluster_profit | 125 | 125 | PASS | selected rows present in final portfolio CoreB-bearing rows by CoreB-specific key |
| C89-F004 | final_portfolio_coreb_rows_in_selected_by_coreb_cluster_profit | 125 | 125 | PASS | final portfolio CoreB-bearing rows match selected rows by CoreB-specific key |
| C89-F005 | 13c_final_sot_component_coreb_only | 117 | 117 | PASS | 8 rows are CORE_A_CORE_B_CONFLUENCE and 117 CORE_B_ONLY; confluence rows have CoreB fields but blank same_count/unique_origin fields. |
| C89-F006 | 13c_final_sot_component_corea_coreb_confluence | 8 | 8 | PASS | Confluence rows still preserve coreb_cluster_id and coreb_profit_r; do not join on generic source_cluster_id/top_candidate_id for these rows. |

Important: final SOT confluence rows should be matched using CoreB-specific fields (`coreb_cluster_id`, `coreb_profit_r`). They should not be matched using generic `source_cluster_id`, generic `top_candidate_id`, or generic `same_count`, because confluence rows may carry CoreA/source fields in those generic columns.

## Feature parity carry-forward

| reference | year_group | feature | calc_variant | rows | exact_1e6 | exact_ratio | note |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| coreb_refined_rule_ledgers | 2025 | range96 | range96_inc | 300 | 250 | 0.833333 | partial |
| coreb_refined_rule_ledgers | 2025 | range192 | range192_inc | 300 | 250 | 0.833333 | partial |
| coreb_refined_rule_ledgers | 2025 | adx14 | adx14_roll_inc | 300 | 198 | 0.66 | partial |
| coreb_refined_rule_ledgers | 2025 | atr14 | atr14_inc | 300 | 198 | 0.66 | partial |
| coreb_refined_rule_ledgers | 2026 | range96 | range96_exc | 195 | 194 | 0.994872 | strong |
| coreb_refined_rule_ledgers | 2026 | range192 | range192_exc | 195 | 194 | 0.994872 | strong |
| coreb_refined_rule_ledgers | 2026 | adx14 | adx14_wilder_exc | 195 | 194 | 0.994872 | strong |
| coreb_refined_rule_ledgers | 2026 | atr14 | atr14_exc | 195 | 194 | 0.994872 | strong |

## Readiness matrix

| gate | status | detail |
| --- | --- | --- |
| CoreB_direct_sot_metrics | READY | 125 selected top-ledger rows produce known WR/PF/totalR. |
| CoreB_topledger_filter_parity | PASS | Selected 125 rows exactly equal rr125_top_ledgers policy=RR125_from_RR1_rules & filter=same_count>=15. |
| CoreB_final_sot_join | PASS | Selected 125 rows match 13C final SOT and final portfolio CoreB-bearing rows by CoreB-specific key: dataset+entry_time+coreb_cluster_id+coreb_profit_r. |
| raw_rr125_universe_replay | PROVEN_EXACT | 25C84 reproduced 16875 raw rows from OHLC+33 rules. |
| raw_condition_replay | PASSED_THRESHOLD_LEVEL | 25C82 all 16875 rows passed stored conditions under inclusive M15/M5. |
| raw_outcome_replay | NEAR_EXACT | 25C80 reproduced 16871/16875 raw profit/exit rows; WR exact and PF delta small. |
| feature_value_parity | PARTIAL | 2026 CoreB feature parity strong; 2025 partial; exact source feature values for all fields not fully available. |
| cluster_representative_live_formula | BLOCKED | same_count/cluster membership/representative profit generation logic not recovered. |
| A002_in_coreb_main_path | DEMOTED | A002 is auxiliary evidence only, not CoreB performance path. |
| live_final_signal | OFF | No Discord/MT5/AI/live hook/final signal. |

## Blockers

| blocker_id | component | status | severity | detail |
| --- | --- | --- | --- | --- |
| 25C89-B001 | CoreB_live_replay | OPEN | HARD | Original cluster representative logic still missing; cannot compute future same_count/representative profit live. |
| 25C89-B002 | Feature_value_parity | PARTIAL | MEDIUM | CoreB 2026 parity high, 2025 partial; full value-level feature parity not proven. |
| 25C89-B003 | A002_performance | DEMOTED | INFO | A002 is not CoreB main path and should not contribute WR/PF. |
| 25C89-B004 | External_actions | OPEN | SAFETY | Discord/MT5/AI/live hook/final signal remain disabled. |

## Interpretation

The 125 CoreB rows are exactly the rows in `rr125_top_ledgers.csv` where:

```text
policy == RR125_from_RR1_rules
filter == same_count>=15
```

They also match the CoreB fields carried into both `gold_v2_13c_coreb_final_sot_rows.csv` and `gold_v2_final_portfolio_2025_2026_sot_ledger.csv` when using the CoreB-specific key:

```text
dataset + entry_time + coreb_cluster_id + coreb_profit_r
```

Therefore CoreB historical SOT performance can be reported cleanly without A002.

What remains blocked is not the historical SOT metric calculation. The blocker is future/live reconstruction of `same_count`, `cluster_id`, and representative profit from OHLC without the original cluster membership algorithm.

## Safety

- audit_only: true
- A002 WR/PF as CoreB: blocked
- CoreB historical SOT report: allowed
- CoreB live evaluator: blocked
- final signal: off
- Discord/MT5/AI/live hook: off

## Next recommended step

`25C90_COREB_DIRECT_SOT_REPORT_AND_LOCAL_SYNC_AUDIT_ONLY`
