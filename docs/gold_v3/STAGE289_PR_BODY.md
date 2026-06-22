## Summary

Stage289 implements the Stage284 balanced + Stage286 strict SHORT safe SHADOW path directly from the existing contractually closed live candle CSVs.

## Runtime source

- goldsharp_m1.csv
- goldsharp_m5.csv
- goldsharp_m15.csv
- goldsharp_h1.csv
- goldsharp_h4.csv
- goldsharp_d1.csv
- optional Stage286 inputs: us500cashsharp_m15.csv and us100cashsharp_m15.csv

The latest CSV row is closed by contract. It is retained and no open-bar guess is applied.

## Local ML

The first BAT run trains Stage280 and Stage281 LightGBM locally from closed candle history. Fit ends before 2025-07-01 and calibration ends before 2026-01-01. 2026 is not used for fit or threshold calibration.

SHADOW starts only when the expected Stage280/281 threshold and fixture-score parity checks pass. A mismatch returns BLOCKED and no fallback model is used.

## Safe admission

- one unresolved candidate maximum
- Stage280/281 combined resolved DD <= 30
- shared 12-hour candidate cooldown
- Stage281 only after a resolved BASE loss within 72 hours
- Stage286 combined resolved DD <= 10
- Stage286 24-hour lockout after a resolved candidate loss
- all state uses exit_dt <= current entry_dt

A resolved BASE adapter is required. Without it, candidate detection runs but admissions are rejected and status is PARTIAL; candidate-only equity is not used as fallback.

## Safety

Audit/SHADOW only. No MT5 order, Discord, final signal, live-ready flag or partial close.

## Verification

Five unit tests pass. Full-history first-run training was started in the container but exceeded the container execution limit, so complete training duration is not claimed as validated here. The local parity gate prevents an incomplete or mismatched model from being used.
