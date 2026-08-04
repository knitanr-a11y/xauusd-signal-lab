# GOLD CHALLENGER C1 V2 DATA V3 — Phase 0 Source Audit

Date: 2026-08-01  
Candidate: `GOLD_CHALLENGER_C1_V2_DATA_V3`

## Formal source decision

The original `(2)` candle inputs used by the earlier V10 research are unavailable. The old 123-trade result is therefore not a reproduction target and remains `UNEXPECTED_DISCOVERY_DIAGNOSTIC` only.

The `(3)` candle set is a new authoritative source set. Results from it belong to a separate candidate and must not be tuned toward the old 123 trades.

## Read-only boundaries

- The running V19 clone and local state were not accessed or modified.
- No V19 bootstrap, P90 threshold, wave grammar, state, ledger, or notification path was changed.
- Phase 0 made no GitHub writes.
- No runtime, BAT, Discord, AI, or MT5 order implementation is part of this research package.

## Source validation

All raw `(3)` candle files in `config/source_manifest.json` were hashed and checked for row count, first/last timestamp, duplicate timestamps, and ascending order. Overlapping old/sharp records were required to be identical; conflicts fail closed.

`goldsharp_m15(3).csv` does not exist. The initial sharp-M1-only M15 derivation was rejected before result calculation because its first bucket began at 01:08 and conflicted with the existing old M15 01:00 bucket. That failure is preserved in:

- `outputs/phase0_m15_sharp_only_overlap_conflicts.csv`
- `outputs/phase0_source_merge_correction.json`

The authoritative correction was fixed before results:

1. validate exact old/sharp M1 overlaps;
2. build the complete deduplicated DATA_V3 M1 union;
3. aggregate the full union by M15 open timestamp;
4. use first/max/min/last for OHLC, sum for tick/real volume, and minimum spread.

The resulting M15 source has SHA256:

`544aea77562b1448cd21b368cdf55f2c34935e445fc6855c4226bb6c27a5f41f`

It reproduces all 81,781 existing old `(3)` broker M15 rows exactly across every derived field.

## Time semantics

CSV `time` is bar-open time. A bar opened at `T` becomes usable only at `T + timeframe`. A closed M15 bar opened at 09:00 becomes available at 09:15, and the decision maps to the exact M1 open timestamped 09:15. H1 and H4 rows are usable only when their bar-close time is not later than the decision timestamp.
