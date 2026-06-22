# GOLD V3 Stage289 runtime hardening audit

Status: `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY`

## Correct live source

Stage289 reads the already existing MT5/MQL5 Files candle CSVs directly:

- `goldsharp_m1.csv`
- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

`time` is the broker/MT5 server bar-open timestamp. Every valid CSV row, including the newest valid row, is closed by contract. Runtime does not remove the latest row by clock inference.

Stage286 additionally requires `us500cashsharp_m15.csv` and `us100cashsharp_m15.csv`. If either is absent or invalid, Stage286 is unavailable and status is PARTIAL. No external-source fallback is allowed; Stage280 and Stage281 remain detectable.

## Hardening changes

1. Replaced the permissive comma-only reader with an append-safe reader.
   - comma, semicolon and tab detection
   - incomplete trailing append row removed
   - latest complete row retained
   - monotonic time required; no silent sorting
   - duplicate OHLC conflicts reported
   - nominal close-time availability preserved
2. Model files are not trusted by existence alone.
   - training report must be PASS
   - frozen threshold and fixture-score parity checked at 1e-12
   - model SHA256 checked against each contract
   - model and contract SHA256 checked against the training report
   - empty or duplicated feature contracts are rejected
3. BASE portfolio state is explicit.
   - `--base-resolved-csv`
   - or `GOLD_V3_BASE_RESOLVED_CSV`
   - or `FX_OUTPUTS/gold_v3/289c/gold_v3_289_base_resolved_import.csv`
   - required columns: `entry_dt`, `exit_dt`, `pnl`
   - no candidate-only-equity fallback
4. State is resolved-only.
   - only `exit_dt <= current entry_dt`
   - a future ledger entry cannot trigger an earlier cooldown
   - Stage281 requires the latest resolved BASE loss within 72h
   - Stage286 uses DD10 and 24h after a resolved accepted candidate loss
5. Hard blockers do not advance the runtime watermark.

## Verification

Local hardening test result: `10 passed`.

Covered cases include:

- semicolon live CSV
- partial trailing MT5 append
- latest complete row retained
- out-of-order input blocked
- H4 available only after nominal close
- model SHA tamper blocked
- future candidate entry does not leak into prior state
- Stage281 resolved BASE-loss gate
- Stage286 DD10 gate
- 2026 excluded from fit/calibration

Full first-run LightGBM training on the user's live-history files has not been claimed as completed in this environment. The BAT trains locally from those files and blocks unless the exact frozen parity checks pass.

## Safety

- audit-only
- SHADOW only
- no MT5 API or order send
- no Discord
- no final signal
- no partial close
- no source CSV mutation
