# GOLD V3 32 requested active candidate loss-feature pruning audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_SPEC_READY_AUDIT_ONLY`

## Purpose

Implement the user-requested six loss-feature pruning groups while keeping all seven Stage31 candidates active.

This stage is still an audit-only win-rate / PF uplift test. It does not approve production use and does not remove any candidate from the candidate set.

## Active candidates remain unchanged

All seven Stage31 candidates remain active:

```text
1, 4, 7, 8, 9, 11, 13
```

## Requested pruning groups

```text
C01: packet 1  -> exclude jst_weekday=Saturday
C02: packet 13 -> exclude rank 2 m15_atr28 in [3.828, 3.953)
C03: packet 8  -> exclude entry_month=2025-02, historical diagnostic only
C04: packet 7  -> exclude entry_month=2025-02, historical diagnostic only
C05: packet 4 and packet 7 -> exclude jst_weekday=Saturday
C06: packet 9 and packet 11 -> exclude source_rank=2
```

Historical month cuts are measured only as diagnostic loss-segment pruning. They are not live-ready filters.

## Required upstream

```text
GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_READY_AUDIT_ONLY
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/31_all_active_candidate_uplift_queue_audit_only/gold_v3_31_summary.json
Files/FX_OUTPUTS/gold_v3/31_all_active_candidate_uplift_queue_audit_only/gold_v3_31_all_active_candidate_set.csv
Files/FX_OUTPUTS/gold_v3/31_all_active_candidate_uplift_queue_audit_only/gold_v3_31_all_active_filter_contract.csv
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_trade_ledger.csv
```

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/32_requested_active_candidate_loss_feature_pruning_audit_only/
```

## Outputs

```text
gold_v3_32_summary.json
gold_v3_32_input_inventory.csv
gold_v3_32_requested_cut_plan.csv
gold_v3_32_per_packet_cut_application.csv
gold_v3_32_before_after_metrics.csv
gold_v3_32_removed_segment_metrics.csv
gold_v3_32_after_monthly_metrics.csv
gold_v3_32_review_matrix.csv
gold_v3_32_blocker_matrix.csv
GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY_REPORT.md
```

## Ready status

```text
GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY
```

## Safety

Audit-only. No order sending, no alert sending, no AI API, no model training, no final signal, no daily cap, no production month filter, no candidate removal.
