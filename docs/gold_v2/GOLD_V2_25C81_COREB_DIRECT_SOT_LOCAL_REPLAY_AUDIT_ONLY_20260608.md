# GOLD V2 25C81 CoreB direct SOT local replay audit-only spec

Created: 2026-06-08

Status: `COREB_DIRECT_SOT_LOCAL_REPLAY_SPEC_READY_AUDIT_ONLY`

## Purpose

Run the first local-official replay step after the 25C80 local sync checkpoint.

This step intentionally ignores A002 for performance evaluation and verifies CoreB by the direct historical SOT route only.

## Official local carry-forward

The official local chain was verified at 25C80 as:

```text
local_official_status = 25C79_A002_ID_JOIN_BLOCKED
later_chat_evidence_adopted = false
coreb_direct_sot_inputs_ready = true
```

25C81 is the first local replay package that may promote CoreB direct SOT parity to local-official status if all checks pass.

## Inputs

The script resolves these files under `Files/FX_OUTPUTS`:

```text
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
gold_v2_13c_coreb_final_sot_rows.csv
gold_v2_final_portfolio_2025_2026_sot_ledger.csv
rr125_top_ledgers.csv
rr125_raw_signal_ledger.csv
25c80_local_sync_summary.json
```

## CoreB direct SOT definition

CoreB direct historical SOT is defined as:

```text
selected file: gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
profit column: profit
```

The matching top-ledger filter is:

```text
rr125_top_ledgers.csv
policy == RR125_from_RR1_rules
filter == same_count>=15
```

Expected count:

```text
125 rows
2025 = 104
2026 = 21
```

## Expected metrics

```text
2025: count 104, WR 72.1154%, PF 3.443512, total R 143.0175
2026: count 21,  WR 80.9524%, PF 5.153846, total R 40.5
total: count 125, WR 73.6%, PF 3.687740, total R 183.5175
```

## Checks

25C81 must verify:

1. 25C80 sync checkpoint is present and says `coreb_direct_sot_inputs_ready = true`.
2. selected top-ledger row count is 125.
3. top-ledger filter row count is 125.
4. selected set equals top-ledger filtered set by:

```text
dataset + entry_time + cluster_id + top_candidate_id + profit + filter + policy
```

5. selected rows match 13C final SOT CoreB fields by:

```text
dataset + entry_time + coreb_cluster_id + coreb_profit_r
```

6. selected rows match final portfolio CoreB-bearing rows by the same CoreB-specific key.
7. A002 remains demoted and unused for CoreB WR/PF.
8. live/final/external actions remain off.

## Outputs

Default output folder:

```text
Files/FX_OUTPUTS/gold_v2_25c81_coreb_direct_sot_local_replay_audit_only
```

Expected files:

```text
GOLD_V2_25C81_COREB_DIRECT_SOT_LOCAL_REPLAY_AUDIT_ONLY_REPORT.md
25c81_summary.json
25c81_input_inventory.csv
25c81_coreb_direct_metrics.csv
25c81_top_filter_parity.csv
25c81_final_sot_join_parity.csv
25c81_readiness_matrix.csv
25c81_guardrail_matrix.csv
```

## Success status

```text
COREB_DIRECT_SOT_LOCAL_REPLAY_PASSED_AUDIT_ONLY_LIVE_BLOCKED
```

## Guardrails

- A002 performance is not used.
- CoreB historical SOT reporting may be locally accepted if checks pass.
- CoreB live evaluator remains blocked.
- No Discord, MT5, AI API, live hook, or final signal.
