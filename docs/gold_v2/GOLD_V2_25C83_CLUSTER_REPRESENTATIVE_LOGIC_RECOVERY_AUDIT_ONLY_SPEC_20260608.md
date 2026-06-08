# GOLD V2 25C83 cluster representative logic recovery audit-only spec

Created: 2026-06-08

Status: `CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_SPEC_READY_AUDIT_ONLY`

## Purpose

After 25C82, CoreB historical SOT is locally reportable from 125 direct rows. The remaining blocker is live/future reconstruction of the top-ledger representative logic.

25C83 audits only this missing logic:

```text
rr125_raw_signal_ledger.csv
  -> cluster_id
  -> same_count
  -> representative profit
  -> rr125_top_ledgers.csv
  -> policy=RR125_from_RR1_rules / filter=same_count>=15
  -> CoreB 125 historical SOT
```

A002 is not used.

## Required upstream state

```text
25C82_LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_READY_AUDIT_ONLY_LIVE_BLOCKED
```

## Inputs

Resolve from `Files/FX_OUTPUTS`:

```text
25c82_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
gold_v2_13c_coreb_final_sot_rows.csv
```

## Audit questions

1. Is `same_count` equivalent to any obvious raw grouping count?
2. Is `source_rule_count` equivalent to any obvious raw grouping count?
3. Can `cluster_id` be reconstructed from raw rows using obvious connected-component or grouped keys?
4. Can `top_candidate_id` / `profit` be selected from raw rows by a simple representative rule?
5. Is a full raw -> top-ledger generator source present locally?

## Required output

The script should produce:

```text
GOLD_V2_25C83_CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_AUDIT_ONLY_REPORT.md
25c83_summary.json
25c83_input_inventory.csv
25c83_top_row_column_profile.csv
25c83_raw_to_top_binding_attempts.csv
25c83_same_count_candidate_tests.csv
25c83_representative_profit_candidate_tests.csv
25c83_recovery_decision_matrix.csv
25c83_blocker_matrix.csv
```

## Success definition

The only success that unblocks live recovery would be:

```text
raw -> cluster_id / same_count / representative profit -> top-ledger 125 rows reproduced exactly by a source-backed rule
```

Without that, the correct status is:

```text
CLUSTER_REPRESENTATIVE_LOGIC_NOT_RECOVERED_AUDIT_ONLY_LIVE_BLOCKED
```

## Guardrails

- No approximate same_count promotion.
- No invented representative profit promotion.
- No A002 performance use.
- No source recovery approval.
- No Discord/MT5/AI/live hook/final signal.
