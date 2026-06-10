# GOLD V3 43 exact entry and prune contract for honmei set audit-only report

Created JST: 2026-06-10

## Status

`GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY_BLOCKED_SOURCE_ARTIFACTS_MISSING`

This Stage43 packet is **audit-only** and **blocked**. It does **not** create a usable live/trading contract.

## Safety state

- GOLD V3 remains source-of-truth constrained.
- GOLD V2 / old GOLD / DISC8 were not read, used, referenced, or used as fallback.
- No OHLC-only approximation was used.
- Stage41 feature-only snapshot was not used as a trading source.
- No live code was created.
- No Discord live enablement was created.
- No MT5 BAT was created.
- No MT5 order path was enabled.
- `live_allowed` remains `False`.

## Inputs read successfully

The following repository files were read successfully:

| Stage | File | Use |
| --- | --- | --- |
| Handoff | `NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md` | Stage43 task/honmei context |
| Handoff | `NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_MUST_READ_SOURCE_CHECK_ADDENDUM_20260610.md` | Required source-check list and stopping rules |
| Handoff | `NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_STAGE01_40_READCHECK_ADDENDUM_20260610.md` | Stage1-40 read-check/safety context |
| Handoff | `NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_FINAL_READ_ORDER_AND_PROMPT_FIX_20260610.md` | Final read order and prompt override |
| Stage42 | `gold_v3_42_primary_plus_restore_candidate_decision.csv` | Human decision rows |
| Stage42 | `GOLD_V3_42_PRIMARY_PLUS_RESTORE_CANDIDATE_DECISION_AUDIT_ONLY_20260610.md` | Human decision report |

## Stage42 honmei decision verified

| decision_role | candidate_label | packet_row | source_scenario_key | variant_key | cooldown | source_stage | source_status | PF | WR | trades/day | negative_months | July PF | live_allowed |
| --- | --- | ---: | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| HONMEI_ADD | `R03_P1_R1_ONLY_CD60_PRUNE_111` | 1 | `R1_ONLY_CD60_PRUNE_111` | `R1_ONLY_CD60_PRUNE_111__R1_ONLY_CD60_PRUNE_111_S021__R1_ONLY_CD60_PRUNE_111_S022` | 60 | Stage36 | ACTIVE_CANDIDATE | 2.6083250034 | 0.6684636119 | 2.0784313725 | 0 | 1.2486063766 | False |
| HONMEI_ADD | `R04_P4_R1_ONLY_CD60_PRUNE_115` | 4 | `R1_ONLY_CD60_PRUNE_115` | `R1_ONLY_CD60_PRUNE_115__R1_ONLY_CD60_PRUNE_115_S020__R1_ONLY_CD60_PRUNE_115_S022` | 60 | Stage36 | ACTIVE_CANDIDATE | 2.5517460463 | 0.6688918558 | 2.0980392157 | 0 | 1.2416950739 | False |
| HONMEI_RESTORE | `R1_ONLY_CD90_PRUNE_050_RESTORE` |  | `R1_ONLY_CD90_PRUNE_050` | `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024` | 90 | Stage22 | REQUEST_MORE_AUDIT_LOW_FREQUENCY | 2.8726383868 | 0.6418219462 | 1.3529411765 | 0 | 5.5905567301 | False |

These Stage42 rows verify only the human decision metadata. They do **not** verify the exact base entry family or prune filters.

## Required source-of-truth artifacts not available in the checked context

The Stage43 handoff/addenda explicitly require Stage15/21/22/30/35/36 source-of-truth artifacts before creating the exact contract. In the available GitHub connector context, the required artifacts below were not readable from the checked repository paths:

| Stage | Required artifact examples | Result |
| --- | --- | --- |
| Stage15 | `GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_REPORT.md`, `gold_v3_15_replay_candidate_metrics.csv`, `gold_v3_15_replay_trade_ledger.csv` | Not found/readable in checked GitHub paths |
| Stage21 | `gold_v3_21_filter_traceability.csv` | Not found/readable in checked GitHub paths |
| Stage22 | `gold_v3_22_filter_traceability.csv`, `gold_v3_22_further_pruned_candidate_metrics.csv` | Not found/readable in checked GitHub paths |
| Stage30 | `gold_v3_30_all_retained_candidate_set.csv`, `gold_v3_30_all_retained_filter_contract.csv` | Not found/readable in checked GitHub paths |
| Stage35 | `gold_v3_35_before_after_metrics.csv`, `gold_v3_35_selected_cut_plan.csv` | Not found/readable in checked GitHub paths |
| Stage36 | `gold_v3_36_ranked_candidate_contract.csv`, `gold_v3_36_final_filter_contract.csv`, `GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY_REPORT.md` | Not found/readable in checked GitHub paths |

The handoff warns these may exist only under the user's local GOLD V3 runtime output root. This environment cannot read that local Windows path directly.

## Why exact contract rows were not emitted

Stage43 stopping conditions require source verification of:

1. source_rank 1 base entry family, direction, profile, and replay ledger from Stage15;
2. Stage21 F002/F003/F004/F006 definitions;
3. Stage22 S020/S021/S022/S024/S030 definitions and restore metrics;
4. Stage30 retained filter contract for R03/R04;
5. Stage35 pruning context;
6. Stage36 ranked active candidate contract and final filters for R03/R04;
7. the Stage22/Stage36 boundary for the CD90 restore candidate.

Because these were not verified from source-of-truth artifacts, the exact contract is intentionally blocked. The CSV/JSON contract outputs contain blocked candidate-level rows only and must not be used by any live evaluator.

## Output files created by this blocked Stage43 packet

- `gold_v3_43_honmei_exact_entry_prune_contract.csv`
- `gold_v3_43_honmei_exact_entry_prune_contract.json`
- `GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY_REPORT.md`
- `gold_v3_43_input_inventory.csv`
- `gold_v3_43_blocker_matrix.csv`
- `gold_v3_43_summary.json`

## Required resolution before unblocking Stage43

Provide the required Stage15/21/22/30/35/36 artifacts from the local GOLD V3 runtime output root, or commit them to a non-quarantined GOLD V3 path. After that, Stage43 should be rerun to create a real exact entry/prune contract.

Until then:

`LIVE BLOCKED / EXACT CONTRACT BLOCKED / MT5 BLOCKED / DISCORD LIVE BLOCKED`
