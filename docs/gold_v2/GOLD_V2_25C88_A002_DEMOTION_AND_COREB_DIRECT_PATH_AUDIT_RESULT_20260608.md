# GOLD V2 25C88 A002 demotion and CoreB direct path audit-only report

Created UTC: 2026-06-08T09:17:05.770843+00:00

Status: `A002_DEMOTED_COREB_DIRECT_SOT_PATH_RESTORED_AUDIT_ONLY`

## Purpose

Move A002 out of the CoreB main path. A002 is useful evidence that the raw RR125 universe and broad event membership are reproducible, but it should not be used as the CoreB performance source because its representative profit remains unresolved.

This is audit-only. It does not approve source recovery, live evaluator, final signal, Discord, MT5, AI, or live hook.

## Final decision

```text
A002 = auxiliary evidence only
CoreB main path = 13C selected top-ledger 125-row historical SOT
A002 WR/PF as original CoreB = not allowed
CoreB live evaluator = still blocked until cluster representative logic is found or a separately-labelled new policy is approved
```

## Why A002 is demoted

A002 membership has strong evidence:

- 772 events are reproduced from raw RR125 rules.
- raw RR125 universe of 16875 rows is reproduced from OHLC + 33 raw rules.

But A002 is a broad event set. One event can map to multiple raw rows, and the original representative profit rule was not found. Therefore A002 can explain the neighborhood of CoreB, but it should not be treated as CoreB.

## CoreB direct SOT metrics

Use `gold_v2_13c_coreb_rr125_selected_top_ledgers.csv` as the direct historical CoreB baseline.

| scope | dataset | profit_column | count | wins | losses | breakeven | win_rate | pf | total_r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CoreB_13C_selected_top_ledgers | 2025 | profit | 104 | 75 | 29 | 0 | 0.7211538461538461 | 3.4435122137908913 | 143.0174666666666 |
| CoreB_13C_selected_top_ledgers | 2026 | profit | 21 | 17 | 4 | 0 | 0.8095238095238095 | 5.153846153846154 | 40.5 |
| CoreB_13C_selected_top_ledgers | total | profit | 125 | 92 | 33 | 0 | 0.736 | 3.687740189339502 | 183.5174666666666 |

## Final portfolio SOT metrics carry-forward

| scope | dataset | profit_column | count | wins | losses | breakeven | win_rate | pf | total_r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Final_Portfolio_SOT | 2025 | profit_r | 346 | 239 | 103 | 4 | 0.6907514450867052 | 2.8390478156443435 | 439.5091333333332 |
| Final_Portfolio_SOT | 2026 | profit_r | 183 | 132 | 44 | 7 | 0.7213114754098361 | 3.6533333333333333 | 248.75 |
| Final_Portfolio_SOT | total | profit_r | 529 | 371 | 147 | 11 | 0.7013232514177694 | 3.0684758347926087 | 688.2591333333332 |

## Status matrix

| artifact_or_route | current_role | new_role | status | evidence | allowed_use | blocked_use |
| --- | --- | --- | --- | --- | --- | --- |
| A002_FIXED_SCOPE_EVENT_SET | candidate event-set / broad CoreB neighborhood | AUXILIARY_EVIDENCE_ONLY | DEMOTE_FROM_COREB_MAIN_PATH | 25C83/25C84 exact membership replay; profit binding blocked | membership density/context only; no WR/PF as original SOT | do not call CoreB; do not use as strategy performance |
| rr125_raw_signal_ledger.csv | raw RR125 rule universe source | RAW_RULE_SOURCE_FOR_REPLAY | KEEP_AS_SOURCE_CONTEXT | 25C84 exact 16875 row replay from OHLC+33 rules | raw rule universe and condition replay | event-level representative result without binding rule |
| rr125_top_ledgers.csv | cluster/top representative summary | HISTORICAL_TOP_LEDGER_SOT_CONTEXT | KEEP_BUT_NOT_FULL_LIVE_REPLAY | threshold-valid but representative/cluster logic not found | historical CoreB SOT evidence and 125-row selected top ledger input | do not derive live same_count/representative profit by approximation |
| gold_v2_13c_coreb_rr125_selected_top_ledgers.csv | CoreB selected 125 rows | COREB_DIRECT_SOT_METRIC_SOURCE | PROMOTE_TO_COREB_MAIN_PATH | direct CoreB historical SOT metrics match 13C | CoreB historical WR/PF/TotalR; direct report baseline | not a live evaluator by itself |
| gold_v2_final_portfolio_2025_2026_sot_ledger.csv | final portfolio SOT | PORTFOLIO_SOT_METRIC_SOURCE | KEEP_AS_FINAL_PORTFOLIO_BASELINE | direct final SOT metrics aggregate consistently | portfolio SOT metrics/report baseline | not proof of full OHLC membership replay |
| CoreB_live_evaluator_path | desired future replay | BLOCKED_UNTIL_CLUSTER_LOGIC_OR_ALTERNATIVE_POLICY | BLOCKED | 13C5 true original clustering candidates=0; 25C86 representative logic not found | audit planning only | no live/final/external actions |

## CoreB direct path plan

| step | action | why | output |
| --- | --- | --- | --- |
| 25C88-D001 | Demote A002 to auxiliary evidence | A002 is broad 772 event set with unresolved representative profit; it is not CoreB main SOT | A002 no longer used for CoreB WR/PF |
| 25C88-D002 | Use CoreB 13C selected top-ledger 125 as direct historical SOT baseline | It has known CoreB count/WR/PF and is not polluted by A002 representative ambiguity | CoreB direct SOT metrics table |
| 25C88-D003 | Carry forward cluster representative blocker | CoreB live replay still requires original clustering/membership logic or a newly labelled alternative policy | live remains blocked |
| 25C88-D004 | Do not invent representative profit | Would be approximate reimplementation and not SOT | A002 performance remains non-SOT only |
| 25C88-D005 | Next: CoreB direct SOT parity package | Build clean handoff focused on 125 rows and required missing cluster source, not A002 | 25C89_COREB_DIRECT_SOT_PARITY_PACKAGE_AUDIT_ONLY |

## Guardrails

| gate | status | detail |
| --- | --- | --- |
| audit_only | PASS | No live/final/external action |
| a002_not_coreb | PASS | A002 demoted to auxiliary event set |
| coreb_sot_metric_source | PASS | Use 13C selected top-ledgers for historical CoreB metrics |
| coreb_live | BLOCKED | Cluster representative logic not found |
| a002_wr_pf_original | BLOCKED | Representative profit not original-source-proven |
| discord_mt5_ai_live_hook | OFF | No external actions |

## Next recommended step

`25C89_COREB_DIRECT_SOT_PARITY_PACKAGE_AUDIT_ONLY`

Goal: produce a clean CoreB-only package centered on the 125-row historical SOT, while carrying forward the missing cluster representative logic blocker. A002 should remain outside the CoreB performance path unless explicitly used as a separately-labelled research event set.
