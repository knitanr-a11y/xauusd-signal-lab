# GOLD V2 25C84 deep cluster representative reconstruction audit-only spec

Created: 2026-06-08

Status: `DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_SPEC_READY_AUDIT_ONLY`

## Purpose

25C83 proved that simple same-entry group counts and simple profit aggregations do not recover the CoreB top-ledger representative logic.

25C84 extends the reconstruction attempt. It still does not approve approximate logic or live operation.

## Scope

A002 is not used.

Target:

```text
CoreB 125 selected top-ledger rows
```

Source universe:

```text
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
```

## Search families

25C84 searches these reconstruction families:

1. Time-window raw row counts around each top entry time.
2. Time-window unique-origin counts.
3. Direction/RR/top_candidate_id matching.
4. top_candidate_id mapped to raw `candidate_id` and raw `origin_id`.
5. Representative profit selection under time-window subsets.
6. Cluster id sequence/rank hypotheses.
7. Local repository keyword scan for possible raw->top generator code.

## Success definition

A reconstruction candidate can only be considered meaningful if it reproduces all 125 rows for:

```text
same_count/source_rule_count
representative profit
```

Even then, it is not automatically source-approved. It must be marked:

```text
RECONSTRUCTION_CANDIDATE_FOUND_HUMAN_REVIEW_REQUIRED
```

If no complete candidate is found, live remains blocked.

## Expected outputs

```text
GOLD_V2_25C84_DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_AUDIT_ONLY_REPORT.md
25c84_summary.json
25c84_input_inventory.csv
25c84_window_count_candidate_tests.csv
25c84_window_profit_candidate_tests.csv
25c84_cluster_id_sequence_tests.csv
25c84_logic_keyword_scan.csv
25c84_best_candidate_summary.csv
25c84_recovery_decision_matrix.csv
25c84_blocker_matrix.csv
```

## Guardrails

- Do not promote partial matches.
- Do not call partial candidates source recovery.
- Do not enable live evaluator.
- Do not use A002.
- Do not send Discord/MT5/AI/live/final signals.
