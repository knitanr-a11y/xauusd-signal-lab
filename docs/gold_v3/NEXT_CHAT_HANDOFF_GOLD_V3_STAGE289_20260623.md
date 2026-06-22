# GOLD V3 Stage289 handoff

Status: `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY`

Use the existing closed live CSV files: goldsharp M1/M5/M15/H1/H4/D1. The latest CSV row is closed by contract and must not be removed.

First BAT run trains Stage280 and Stage281 locally from pre-2026 history, checks exact thresholds and fixture scores, and blocks SHADOW if parity fails. Stage286 uses US500 and US100 M15 files when both are present; there is no fallback.

Run `scripts/gold_v3_runtime/bat/run_gold_v3_289_live_candle_ml_safe_shadow.bat`.

Output is `MQL5/Files/FX_OUTPUTS/gold_v3/289c/paste_me.txt`.

A resolved BASE CSV with entry_dt, exit_dt and pnl is required for READY admission. Without it, detection runs but admission is rejected and status is PARTIAL.

Audit-only. No MT5 order, Discord, final signal or partial close.
