# GML1-MLR1 Stage ML-01 — raw-data and timestamp audit

Date: 2026-06-27  
Status: `PASS_WITH_EXPECTED_MARKET_GAPS_AND_RECORDED_HASH_CORRECTION`

Machine-readable authority:

`config/gold_ml_v1/mlr1_stage_ml01_raw_data_audit_20260627.json`

Hash correction authority:

`config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json`

## Result

The fixed M1/M15/H1/H4/D1 snapshot is suitable for proceeding to the causal feature-engine stage.

No model, label table or feature table has been created yet.

## Snapshot

| TF | Rows | First bar-open | Last bar-open |
|---|---:|---|---|
| M1 | 1,225,431 | 2023-01-03 01:00 | 2026-06-19 19:54 |
| M15 | 81,781 | 2023-01-03 01:00 | 2026-06-19 19:45 |
| H1 | 20,459 | 2023-01-03 01:00 | 2026-06-19 19:00 |
| H4 | 5,352 | 2023-01-03 00:00 | 2026-06-19 16:00 |
| D1 | 894 | 2023-01-03 00:00 | 2026-06-19 00:00 |

The H1 and D1 full SHA256 strings in the first ML-00 JSON were transcription errors. They were detected before any feature, label or model implementation and corrected through an append-only correction record.

## Integrity checks

All five timeframes passed:

- identical eight-column schema,
- parseable bar-open timestamps,
- zero duplicate timestamps,
- strictly increasing order,
- correct timeframe alignment,
- zero invalid OHLC rows,
- zero negative or zero spread rows,
- zero nonfinite numeric values.

`real_volume` is zero for every row and is forbidden as an MLR1-v1 feature. `tick_volume` remains available.

## Aggregation parity

The supplied higher-timeframe bars reproduce exactly from the supplied lower-timeframe bars for open, high, low, close and summed tick volume:

- M1 to M15: 81,781 of 81,781 bars matched.
- M15 to H1: 20,459 of 20,459 matched.
- H1 to H4: 5,352 of 5,352 matched.
- H1 to D1: 894 of 894 matched.

Partial bars around session endings are preserved as supplied. They are not padded or interpolated.

## Exact-M1 entry availability

M15 decision points: 81,781.

- exact M1 at decision time: 80,882,
- missing exact M1: 899,
- exact availability: 98.9007%.

Most missing decisions occur at server 00:00 around the daily maintenance break. The last M15 bar produces a 2026-06-19 20:00 decision without exact M1.

All 899 cases must be skipped. Next-M1 fallback remains forbidden.

## Closed higher-timeframe availability

Among exact-M1 decisions, only the earliest rows lack a prior closed bar:

- H1: 3 decisions,
- H4: 11 decisions,
- D1: 91 decisions.

These rows, plus later feature warmup rows, are excluded. No warmup bridge or historical imputation is allowed.

## Gaps

The dominant gaps correspond to daily maintenance, weekends and holidays.

- M1 gaps longer than one minute: 941.
- M15 gaps longer than 15 minutes: 893.
- Maximum M1 gap: 3 days 02:02.
- Maximum M15 gap: 3 days 02:15.

Gaps are part of the market data and must not be forward-filled.

## Spread

M1 spread in points:

- minimum 12,
- median 17,
- p95 27,
- p99 32,
- maximum 270.

High spreads are not silently deleted or clipped. The future feature engine may expose causal spread/ATR and transformed diagnostics, while the raw spread remains the execution-cost source.

## Walk-forward capacity before feature warmup

Each fixed test segment contains more than 10,800 exact-M1 decisions before feature warmup. This is sufficient to proceed with feature and label construction.

## Gate

ML-01 passes.

Next stage:

`ML-02_COMMON_CAUSAL_FEATURE_ENGINE`

Controls remain unchanged:

- audit-only,
- no label engine,
- no model training,
- no portfolio use,
- no live signal,
- no MT5 order,
- no Discord.
