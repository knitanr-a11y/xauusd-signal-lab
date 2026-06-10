# GOLD V3 50 H4 closed-readiness and prior-60D q70 state builder audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_SPEC_READY_AUDIT_ONLY`

## Purpose

Materialize the first two Stage49 state schemas using current local candle CSVs:

1. `h4_closed_readiness_state`
2. `rolling_prior_60d_q70_state`

Stage50 is audit-only. It does not create a live evaluator and does not change the Stage46/47 contract.

## Frozen upstream contract

Stage50 must preserve:

- `htf_asof = closed`
- OPEN asof prohibited
- full Stage45 base + HV sibling candidate pool retained
- no manual candidate demotion/removal
- high-vol profiles retained:
  - `HV_TP180_SL70_H128`
  - `HV_TP200_SL80_H128`
  - `HV_TP220_SL90_H128`
- strict rolling health gate unchanged

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

## Computation contract

### H4 closed readiness

- H4 candle source time is treated as H4 open time.
- Closed-asof usable time is `h4_open_time + 4 hours`.
- A H4 row is usable for an M15 decision only when `feature_time <= m15_time`.
- OPEN asof must not be used.

### Prior 60D q70 high-vol state

Use the Stage45 formula exactly:

```python
m15_atr28 = ATR(28) simple rolling mean of true range
window_bars = 60 * 96
min_periods = max(28, window_bars // 4)
m15_atr28_q70 = m15_atr28.shift(1).rolling(window_bars, min_periods=min_periods).quantile(0.70)
is_high_vol = (m15_atr28 >= m15_atr28_q70) & m15_atr28_q70.notna()
```

The `.shift(1)` is mandatory to prevent current-bar leakage.

## Required inputs

- `goldsharp_m15.csv`
- `goldsharp_h4.csv`
- Stage46 contract output
- Stage47 forward audit output
- Stage49 state schema output

## Outputs

Default output folder:

`Files\FX_OUTPUTS\gold_v3\50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only`

Files:

- `gold_v3_50_h4_closed_readiness_state.csv`
- `gold_v3_50_rolling_prior_60d_q70_state.csv`
- `gold_v3_50_high_vol_state_summary.csv`
- `gold_v3_50_validation_matrix.csv`
- `gold_v3_50_state_builder_summary.json`
- `gold_v3_50_PASTE_ME_STATE_BUILDER_SUMMARY.txt`
- `GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_AUDIT_ONLY_REPORT.md`

## Validation

Stage50 validates:

1. Stage46/47/49 are READY.
2. OPEN asof is not allowed.
3. Candidate pool was not mutated.
4. M15/H4 input files exist and have required OHLC columns.
5. H4 closed feature time is `time + 4h`.
6. q70 state uses `shift(1)`, not current bar.
7. q70 state has no value before minimum history.
8. The generated state has high-vol pass/fail values after sufficient history.

## Interpretation

READY means the H4 readiness state and prior-60D q70 state have been generated and validated for audit-only use.
It does not approve live trading.

## Next stage

Stage51 should build the full-candidate virtual opportunity ledger using the Stage50 state artifacts, still audit-only.
