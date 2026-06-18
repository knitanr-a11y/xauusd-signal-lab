# GOLD V3 Stage240 - Stage199 ABC Primary + SCALP Secondary Latest State Bridge

Created JST: 2026-06-19

Stage name:

`GOLD_V3_240_STAGE199_ABC_PRIMARY_SCALP_SECONDARY_LATEST_STATE_BRIDGE`

Purpose:

- Use the frozen Stage199 logic, not a substitute detector.
- Evaluate both Stage199 families:
  - `ABC` as PRIMARY / DAYTRADE path
  - `SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED` as SECONDARY / SCALP path
- Write the latest closed M15 state to the Stage217 staging-retention source consumed by Stage227.

Important contract:

- CSV latest row is treated as CLOSED.
- No open/as-of interpretation.
- No GOLD V2 / old GOLD / DISC8 / Stage41 fallback.
- Candidate pool is not removed.
- F002 exclusion is not bypassed.
- Stage240 itself does not send Discord and does not call MT5.

Source logic:

`script/gold_v3_runtime/gold_v3_199_scalp_filtered_v1_ohlc_recomputed_freeze_audit.py`

Actual path:

`scripts/gold_v3_runtime/gold_v3_199_scalp_filtered_v1_ohlc_recomputed_freeze_audit.py`

Output source for Stage227:

`FX_OUTPUTS/gold_v3/217/staging_retention/latest_state.json`

Selection priority:

1. ABC latest signal if present.
2. SCALP latest signal if present.
3. NO_SIGNAL with the latest M15 timestamp.

ABC is written as `strategy_role=DAYTRADE_PRIMARY_ABC`.
SCALP is written as `strategy_role=SCALP_SECONDARY_WATCHLIST`.
