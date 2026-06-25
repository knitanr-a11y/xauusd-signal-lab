# GOLD_ML_V1 Exploration Batch024 CI PASS — User Run Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_026_EXPLORATION_BATCH024_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

## Authorization and scope

The user explicitly authorized new candidate exploration after the frozen nine completed cost stress, fresh prospective confirmation, and stateful-monitor initialization.

Authorization record:

`config/gold_ml_v1/exploration_batch024_authorization_20260625.json`

The authorization is limited to:

`EXPLORATION_BATCH024_M15_H1_PULLBACK_ONLY`

The existing frozen nine candidates, their IDs, rules, thresholds, histories and monitoring ledger must not be modified.

## Predeclared search family

Batch024 is a new lineage:

`M15_H1_TREND_PULLBACK_LINEAGE_EXP024`

It is intentionally separate from the frozen M15-H4 and H1-D1 breakout lineages.

The new family uses:

- H1 confirmed EMA20/EMA50 trend direction;
- H1 EMA gap normalized by Wilder ATR14;
- M15 Wilder RSI14 pullback re-entry;
- optional M15 EMA20 touch-and-reclose confirmation;
- exact M1 execution;
- one open position per cell;
- same-M1 TP/SL priority: SL;
- fixed SL 1.0R, TP 1.5R, horizon 720 minutes.

## Frozen search grid

Configuration:

`config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json`

Full Cartesian grid:

- directions: LONG, SHORT;
- H1 normalized gap: 0.00, 0.15, 0.30;
- M15 long RSI re-entry level: 35, 40, 45;
- SHORT uses the mirror level `100-long_level`;
- trigger modes: RSI cross only, EMA20 touch-and-reclose.

Total attempted cells:

`2 × 3 × 3 × 2 = 36`

Every cell has a separate `GML1-EXP024-*` ID. Every failed cell, null result, suppressed signal, missing exact-M1 entry, unresolved 2026 row and survivor must remain in output.

## Frozen year contract

- 2023: exploration only;
- 2024: validation only, no retune;
- 2025: final test only, no retune;
- 2026: diagnostic only, never retune.

Predeclared gates:

2023:

- resolved trades >= 24;
- PF >= 1.10;
- mean R > 0.05.

2024 and 2025 independently:

- resolved trades >= 18;
- PF >= 1.00;
- mean R > 0.

A survivor must pass all three gated years. No survivor is a valid completed exploration result.

All-gate-pass cells remain `RESEARCH_ONLY` pending separate review. They are not automatically accumulated, promoted, registered or added to the frozen nine.

## Inputs

The runner verifies exact SHA-256 for the frozen files:

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`

`WARMUP_BRIDGE_EXACT` is forbidden as an exploration or tuning input.

## Implementation

- `scripts/gold_ml_v1/exploration/batch024_pullback_engine.py`
- `scripts/gold_ml_v1/exploration/run_batch024_pullback_exploration.py`
- `scripts/gold_ml_v1/exploration/windows/run_batch024_pullback_exploration.bat`
- `tests/gold_ml_v1/test_exploration_batch024.py`

CI record:

`config/gold_ml_v1/exploration_batch024_ci_pass_20260625.json`

Validation PR 32 was closed without merge after workflow run `28167936911`, job `83424511552`, passed all existing audit tests plus Batch024 tests.

## One-click run

User-facing entrypoint:

`RUN_GOLD_ML_V1_NEXT.bat`

The internal phase BAT must not be run directly.

Output directory:

`outputs/gold_ml_v1/exploration_batch024_m15_h1_pullback`

Upload file:

`outputs/gold_ml_v1/exploration_batch024_m15_h1_pullback/UPLOAD_THIS_GOLD_ML_V1.txt`

## Required user action

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Drag the selected `UPLOAD_THIS_GOLD_ML_V1.txt` into ChatGPT.

## Still forbidden

- changing or deleting the frozen nine;
- post-result grid or gate changes;
- retuning from 2024, 2025 or 2026;
- same-lineage PF or trade pooling;
- automatic accumulation or promotion;
- live signal, MT5 order, Discord, AI API or live hook.
