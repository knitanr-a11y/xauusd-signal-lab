# GOLD V3 64 M15/M5 alignment state builder audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_SPEC_READY_AUDIT_ONLY`

## Purpose

Build an audit-only M15/M5 alignment state for later live-readiness planning.

Stage64 verifies that closed M15 timestamps can be aligned to M5 timestamps for future TP/SL/horizon adjudication parity checks.

Important input contract inherited from Stage63:

- Open/in-progress candles are not written into CSV files.
- Therefore the latest M15/M5 rows are treated as latest available closed rows under the CSV export contract.

Stage64 does not generate signals and does not adjudicate trades.

## Upstream source of truth

- Stage63 H4 closed-bar state READY
- `goldsharp_m15.csv`
- `goldsharp_m5.csv`

## Non-negotiable safety boundaries

- GOLD V3 remains audit-only.
- No MT5 orders.
- No MT5 execution BAT.
- No Discord live notification.
- No AI API call.
- No live hook.
- No final signal.
- No candidate pool mutation.
- No high-vol profile demotion/removal.
- No GOLD V2 / old GOLD / DISC8.
- No Stage41 feature-only trading source.

## Audit checks

Stage64 checks:

1. Stage63 is READY.
2. M15 and M5 CSV files exist.
3. Both CSV files have data rows.
4. Timestamp columns can be identified.
5. Timestamps parse for all rows.
6. Timestamps are monotonic increasing.
7. Duplicate timestamps are zero.
8. M15 rows inside the M5 time range have matching M5 timestamps.
9. The latest M15 timestamp is covered by the M5 range.
10. Safety flags remain false.

Market-closed/weekend gaps are not considered failures by themselves. The alignment test checks timestamp compatibility, not continuous 24/7 candles.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\64_m15_m5_alignment_state_builder_audit_only`

Files:

- `gold_v3_64_m15_m5_alignment_state.csv`
- `gold_v3_64_m15_m5_alignment_detail.csv`
- `gold_v3_64_csv_inventory.csv`
- `gold_v3_64_validation_matrix.csv`
- `gold_v3_64_alignment_summary.json`
- `gold_v3_64_PASTE_ME_M15_M5_ALIGNMENT_SUMMARY.txt`
- `GOLD_V3_64_REPORT.md`

## Success condition

Stage64 READY means:

- Stage63 is READY.
- M15/M5 CSV timestamps are readable and ordered.
- Every M15 timestamp inside the overlapping M5 time range has a corresponding M5 timestamp.
- Latest M15 is not beyond latest M5.
- No live capability is enabled.

READY does not approve live trading.

## Next stage

Stage65 should implement:

`GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_AUDIT_ONLY`

It must remain audit-only.
