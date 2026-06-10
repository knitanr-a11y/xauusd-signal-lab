# GOLD V3 65 rolling prior-60D Q70 state audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_SPEC_READY_AUDIT_ONLY`

## Purpose

Build an audit-only rolling prior-60D Q70 high-volatility state from closed-only CSV inputs.

Stage65 does not generate trading signals. It only prepares and audits a deterministic rolling high-volatility state for later live-readiness stages.

## Input contract

Inherited from Stage63 and Stage64:

- Open/in-progress candles are not written to CSV.
- CSV open-bar exclusion is not required.
- The latest CSV rows are treated as latest available closed rows under the CSV export contract.

## Upstream source of truth

- Stage64 M15/M5 alignment READY
- `goldsharp_h4.csv`
- `goldsharp_m15.csv`

## Q70 calculation contract

Stage65 computes an H4 volatility metric and prior-60D Q70 threshold:

- Volatility metric: H4 true range when OHLC is available.
- True range: `max(high-low, abs(high-prev_close), abs(low-prev_close))`.
- Fallback is blocked if OHLC columns cannot be detected.
- Rolling Q70 uses prior rows only: current H4 row is excluded.
- Rolling window: timestamp >= current_time - 60 days and timestamp < current_time.
- Minimum prior observations: 20.
- `is_high_vol_q70 = metric >= prior_60d_q70` when minimum prior observations are available.

The Q70 state is then asof-attached to closed M15 timestamps for audit-only downstream use.

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

Stage65 checks:

1. Stage64 is READY.
2. H4 and M15 CSV files exist.
3. Timestamp columns are detected and parseable.
4. OHLC columns are detected for H4.
5. H4 and M15 timestamps are monotonic with no duplicates.
6. Rolling Q70 produces at least one valid row.
7. Latest H4 row has a valid prior-60D Q70 state.
8. M15 asof mapping has no missing H4 Q70 state after the first valid H4 Q70 timestamp.
9. Safety flags remain false.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\65_rolling_prior_60d_q70_state_audit_only`

Files:

- `gold_v3_65_h4_rolling_prior_60d_q70_state.csv`
- `gold_v3_65_m15_asof_q70_state.csv`
- `gold_v3_65_csv_inventory.csv`
- `gold_v3_65_validation_matrix.csv`
- `gold_v3_65_q70_state_summary.json`
- `gold_v3_65_PASTE_ME_Q70_STATE_SUMMARY.txt`
- `GOLD_V3_65_REPORT.md`

## Success condition

Stage65 READY means:

- Stage64 is READY.
- H4 rolling prior-60D Q70 state is computed without open-asof usage.
- Latest H4 row has valid prior-60D Q70.
- M15 asof mapping has valid Q70 coverage after the first valid H4 Q70 timestamp.
- No live capability is enabled.

READY does not approve live trading.

## Next stage

Stage66 should implement:

`GOLD_V3_66_VIRTUAL_MONITORING_STATE_AUDIT_ONLY`

It must remain audit-only.
