# GML1-MLR1 Stage ML-03 — exact-M1 label engine

Date: 2026-06-27  
Status: `IMPLEMENTED_AND_CONTAINER_VALIDATED_USER_PC_PINNED_REPLAY_PENDING`

## GitHub implementation

- Engine: `scripts/gold_ml_v1/mlr1/build_labels.py`
- Frozen contract: `config/gold_ml_v1/mlr1_label_contract_v1_20260627.json`
- Unit tests: `tests/gold_ml_v1/test_mlr1_labels.py`
- Windows runner: `scripts/gold_ml_v1/mlr1/run_build_labels.bat`
- Validation record: `config/gold_ml_v1/mlr1_stage_ml03_label_validation_20260627.json`

## Label geometry

Label ID:

`MLR1_LABEL_6H_TP1P5_SL1P0_ATR14`

For every eligible ML-02 decision, LONG and SHORT are evaluated independently:

- target: 1.50 times decision-time M15 Wilder ATR14,
- protective distance: 1.00 ATR,
- maximum horizon: six wall-clock hours,
- outcomes: TARGET, PROTECTIVE or TIME,
- unresolved snapshot-tail rows are excluded.

## Bid and ask handling

Raw M1 OHLC is bid.

LONG:

- entry is exact M1 bid open plus exact entry spread,
- target and protective touches use M1 bid high/low,
- TIME exit uses M1 bid close.

SHORT:

- entry is exact M1 bid open,
- ask open/high/low/close are reconstructed as bid plus contemporaneous M1 spread,
- target and protective touches use reconstructed ask low/high,
- TIME exit uses reconstructed ask close.

## M1 boundary rules

The entry M1 bar is included.

An M1 bar opening exactly at the six-hour horizon is excluded, because its close occurs after the horizon. The last eligible TIME-exit bar must open strictly before the horizon, so its close is at or before the horizon.

When target and protective are both touched inside the same M1 bar and neither was crossed at the open, PROTECTIVE wins.

## Gap fills

Protective gaps are handled conservatively:

- LONG bid open below the protective level fills at that lower bid open,
- SHORT reconstructed ask open above the protective level fills at that higher ask open.

Targets that are already crossed at the M1 open fill at the target level.

The full snapshot contains:

- 372 LONG protective gap fills,
- 489 SHORT protective gap fills.

These trades can realize less than minus 1R and are not clipped back to minus 1R.

## Cost columns

The registry stores:

- `base_r`: actual bid/ask path with actual spread and no added slippage,
- `strong_r`: additional spread to 2x plus adverse 0.10 price at entry and exit,
- `extreme_r`: additional spread to 3x plus adverse 0.20 price at entry and exit.

Strong and Extreme scenarios do not relabel the market path. They subtract incremental execution cost from the base realized R.

## Resolved-only rule

A TARGET or PROTECTIVE hit before the raw snapshot ends is resolved even when the nominal six-hour horizon extends beyond the snapshot.

A no-hit row is unresolved when its six-hour horizon extends past the last observed M1 close. Such rows are excluded from the label registry.

## Full-snapshot result

ML-02 feature decisions: 74,168.

Potential direction rows: 148,336.

Resolved labels: 148,317.

Unresolved at snapshot tail:

- LONG: 11,
- SHORT: 8.

Outcomes:

| Direction | TARGET | PROTECTIVE | TIME | Resolved |
|---|---:|---:|---:|---:|
| LONG | 26,549 | 42,991 | 4,617 | 74,157 |
| SHORT | 25,123 | 44,675 | 4,362 | 74,160 |

Same-M1 collisions resolved protective-first:

- LONG: 47,
- SHORT: 50.

Expected label-registry SHA256:

`c897a00905ca3edc47eff29a159beff21e1c1aafc66c6c41558ba3dfd2a0d7ed`

Two independent full builds produced the same hash.

## Causality validation

Data was truncated at 2024-12-31 12:00 and labels were rebuilt only through the safe decision cutoff six hours earlier.

- compared rows: 79,926,
- decision/direction keys: identical,
- outcomes: identical,
- maximum persisted numeric difference: approximately 5e-9 from CSV decimal formatting.

No future M1 data changed an earlier outcome.

## Unit tests

Eight ML-03 tests passed. Combined with ML-02, 14 tests passed under the repository-relative layout.

Run from repository root:

```bat
py -3.12 -m unittest tests.gold_ml_v1.test_mlr1_features tests.gold_ml_v1.test_mlr1_labels -v
```

## Windows replay

First build ML-02 features, then run:

```bat
scripts\gold_ml_v1\mlr1\run_build_labels.bat "C:\path\to\raw"
```

Expected output:

`outputs/gold_ml_v1/mlr1/ml03_labels_v1/mlr1_labels_v1.csv.gz`

The user-PC replay must confirm 148,317 rows and the frozen label SHA before cross-environment exact parity is claimed.

## Unconditional baseline diagnostic

Always taking every M15 decision is negative under Strong cost:

| Direction | Strong mean R | Strong PF |
|---|---:|---:|
| LONG | -0.1552 | 0.7666 |
| SHORT | -0.2162 | 0.6889 |

These are not model results. They are the minimum frozen baselines that ML-04 must beat without test-period retuning.

## Controls

- audit-only remains ON,
- no model has been trained,
- no threshold has been selected,
- no candidate stack was modified,
- no portfolio or live use,
- no final signal,
- no MT5 order,
- no Discord.

Next development stage:

`ML-04_DETERMINISTIC_AND_LINEAR_BASELINES`
