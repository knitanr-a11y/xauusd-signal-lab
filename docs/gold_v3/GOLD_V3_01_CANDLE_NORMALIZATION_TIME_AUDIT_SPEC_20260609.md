# GOLD V3 01 candle normalization and time audit spec

Created: 2026-06-09

Status: `GOLD_V3_01_CANDLE_NORMALIZATION_TIME_AUDIT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 Phase 00 completed workspace separation and candle inventory:

```text
status = GOLD_V3_00_WORKSPACE_CANDLE_INVENTORY_READY_AUDIT_ONLY
primary_gold_hash_complete = true
primary_present_timeframes = D1, H1, H4, M1, M15, M5
```

Phase 01 normalizes the primary GOLD# 2025 candle set and audits time alignment before any feature engineering, labels, signals, or exploration.

This step must not use GOLD V2 artifacts and must not generate signals.

## Source-of-truth inputs

Primary input directory:

```text
Files/FX_INPUTS/gold_v3/raw_candles/
```

Required primary files:

```text
gold#_m1.csv
gold#_m5.csv
gold#_m15.csv
gold#_h1.csv
gold#_h4.csv
gold#_d1.csv
fetch_summary.json
```

Expected primary row counts from Phase 00/fetch summary:

```text
M1  = 353074
M5  = 70684
M15 = 23563
H1  = 5894
H4  = 1541
D1  = 258
```

Auxiliary/reference files may be present but are not normalized in Phase 01:

```text
goldsharp_m1/m5/m15/h1/h4/d1.csv
```

## Canonical schema

Write normalized primary candles with the following columns:

```text
symbol
source_set
timeframe
time_utc
time_jst
open
high
low
close
tick_volume
spread
real_volume
bar_index
source_file
source_sha256
```

Rules:

- `symbol = GOLD#`
- `source_set = gold_hash_2025_primary`
- `time_utc` parsed as UTC-aware timestamp string.
- `time_jst` parsed or derived from UTC+9.
- OHLC numeric columns must be numeric and non-null.
- Rows sorted by `time_utc` ascending.
- Duplicate `time_utc` rows are not allowed.

## Time audit checks

For each timeframe:

```text
row_count
expected_row_count
first_time_utc
last_time_utc
duplicate_time_count
non_monotonic_count
null_ohlc_rows
invalid_ohlc_rows where high < max(open, close) or low > min(open, close)
weekend_rows
max_gap_minutes
large_gap_count where gap > expected step * 3
open_minute_mod_ok
```

Expected step minutes:

```text
M1=1, M5=5, M15=15, H1=60, H4=240, D1=1440
```

Open-time convention checks:

```text
M1 minute modulo 1 = 0
M5 minute modulo 5 = 0
M15 minute modulo 15 = 0
H1 minute = 0
H4 minute = 0 and hour modulo 4 = 0
D1 hour = 0 and minute = 0
```

Cross-timeframe containment checks:

```text
M5 open times should be subset of M1 open times
M15 open times should be subset of M5 open times
H1 open times should be subset of M15 open times
H4 open times should be subset of H1 open times
D1 open times should be subset of H4 open times where broker/session calendar allows it
```

D1/H4 mismatch is warning-level because daily open and broker session conventions can differ.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/
```

Output files:

```text
GOLD_V3_01_CANDLE_NORMALIZATION_TIME_AUDIT_REPORT.md
gold_v3_01_summary.json
gold_v3_01_primary_input_inventory.csv
gold_v3_01_normalized_candle_manifest.csv
gold_v3_01_timeframe_audit.csv
gold_v3_01_cross_timeframe_alignment.csv
gold_v3_01_decision_matrix.csv
gold_v3_01_blocker_matrix.csv
canonical_candles/gold_v3_gold_hash_2025_primary_m1.csv
canonical_candles/gold_v3_gold_hash_2025_primary_m5.csv
canonical_candles/gold_v3_gold_hash_2025_primary_m15.csv
canonical_candles/gold_v3_gold_hash_2025_primary_h1.csv
canonical_candles/gold_v3_gold_hash_2025_primary_h4.csv
canonical_candles/gold_v3_gold_hash_2025_primary_d1.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit.zip
```

## Status names

If required primary files are missing or row counts mismatch:

```text
GOLD_V3_01_CANDLE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If primary files are present but hard time/OHLC checks fail:

```text
GOLD_V3_01_CANDLE_TIME_AUDIT_BLOCKED_AUDIT_ONLY
```

If normalization and hard checks pass while warning-level gaps/session differences may remain:

```text
GOLD_V3_01_CANDLE_NORMALIZATION_TIME_AUDIT_READY_AUDIT_ONLY
```

## Hard fail checks

- Missing any primary GOLD# timeframe.
- Row count mismatch against Phase 00 expected primary rows.
- Duplicate `time_utc` rows.
- Non-monotonic time after sorting check cannot be resolved.
- Null OHLC rows.
- Invalid OHLC rows.
- Open-time modulo failure for M1/M5/M15/H1/H4/D1.
- M5 not subset of M1, M15 not subset of M5, H1 not subset of M15, or H4 not subset of H1.

D1/H4 subset mismatch is warning-level unless explicitly promoted later.

## Guardrails

- GOLD V3 only.
- Do not read or reuse GOLD V2 selected/source/final/arbitration artifacts.
- No features, no labels, no candidate exploration, no signals.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- NO_SIGNAL must not notify Discord.
