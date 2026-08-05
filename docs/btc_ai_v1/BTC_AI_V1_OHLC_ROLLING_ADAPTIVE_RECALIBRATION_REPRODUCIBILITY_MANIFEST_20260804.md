# BTC AI V1 — Stage 31 reproducibility manifest

Date: 2026-08-04

## Authority

- frozen contract: `config/btc_ai_v1/ohlc_rolling_adaptive_recalibration_forensic_contract_20260803.json`
- implementation addendum: `config/btc_ai_v1/ohlc_rolling_adaptive_recalibration_implementation_addendum_20260803.json`
- accepted XM `BTCUSD#` source hashes matched `source_data_manifest_20260803.json` exactly.

## Generated state inputs

- `features.npy`: SHA256 `b05953d1067b9d9ae4e4275173c0379d7c87b0a821162d448d9f858566f7a69a`; shape `[125567,100]`; float32
- `meta.csv`: SHA256 `67da530c87a0a0b719e2585075d6e2e0598a8a3c111c5542fae3ba227a1f9333`; 125,567 rows
- `feature_sets.json`: SHA256 `a384b1b7cce8a6bb02d3522537caca9052939eb23120af7cc040bac41fb97665`; 100 features

## Execution

The frozen metric logic was retained. The 192 tasks were executed in eight three-month chunks using process-level parallelism with one LightGBM thread per task because a single long-running shell process exceeded the execution-shell limit. No model, feature, label, training window, calibration method, threshold, metric or gate changed.

Coverage required and obtained:

- 24 months × 4 schedules × 2 directions = 192 unique evaluations;
- all 192 available;
- all leakage counters zero;
- 541,984 prediction-audit rows.

A representative direct recomputation matched the stored metrics to maximum absolute difference `8.33e-17`.

Raw OHLC and generated state arrays are excluded from the research ZIP and must be supplied separately using the frozen hashes.
