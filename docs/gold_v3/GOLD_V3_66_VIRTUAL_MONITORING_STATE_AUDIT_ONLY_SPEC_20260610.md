# GOLD V3 66 virtual monitoring state audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_66_VIRTUAL_MONITORING_STATE_SPEC_READY_AUDIT_ONLY`

## Purpose

Build an audit-only virtual monitoring state from the Stage51 virtual opportunity ledger and the Stage65 rolling prior-60D Q70 state.

Stage66 does not select trades, generate live signals, send Discord notifications, call AI APIs, or place MT5 orders.

It only prepares candidate-level monitoring state for later health-gate rehydration.

## Input contract

Inherited from Stage63-65:

- Open/in-progress candles are not written into CSV files.
- CSV open-bar exclusion is not required.
- All state is audit-only and closed-asof.

## Upstream source of truth

- Stage65 rolling prior-60D Q70 state READY
- Stage51 virtual opportunity ledger
- Stage65 `gold_v3_65_m15_asof_q70_state.csv`

## Candidate monitoring contract

Stage66 should:

1. load the Stage51 virtual opportunity ledger,
2. detect/construct a stable `candidate_key`,
3. detect the opportunity timestamp column,
4. asof-attach Stage65 Q70 state by M15 timestamp,
5. aggregate candidate-level monitoring state,
6. retain all candidates observed in the virtual opportunity ledger,
7. avoid any manual candidate demotion/removal.

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

Stage66 checks:

1. Stage65 is READY.
2. Stage51 virtual opportunity ledger exists.
3. Stage65 M15 asof Q70 state exists.
4. Opportunity timestamps parse for all rows.
5. Candidate key can be constructed.
6. Candidate count is greater than zero.
7. M15 asof Q70 coverage is present after the first valid Q70 timestamp.
8. No candidates are manually removed or demoted.
9. Safety flags remain false.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\66_virtual_monitoring_state_audit_only`

Files:

- `gold_v3_66_virtual_opportunity_q70_joined_ledger.csv`
- `gold_v3_66_candidate_virtual_monitoring_state.csv`
- `gold_v3_66_virtual_monitoring_inventory.csv`
- `gold_v3_66_validation_matrix.csv`
- `gold_v3_66_virtual_monitoring_summary.json`
- `gold_v3_66_PASTE_ME_VIRTUAL_MONITORING_SUMMARY.txt`
- `GOLD_V3_66_REPORT.md`

## Success condition

Stage66 READY means:

- Stage65 is READY.
- Stage51 virtual opportunities are readable and timestamped.
- Candidate monitoring state is built for all observed candidate keys.
- Q70 asof state is attached where available.
- No live capability is enabled.

READY does not approve live trading.

## Next stage

Stage67 should implement:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY`

It must remain audit-only.
