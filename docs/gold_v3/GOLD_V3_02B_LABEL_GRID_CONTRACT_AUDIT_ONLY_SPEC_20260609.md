# GOLD V3 02B label grid contract audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_02B_LABEL_GRID_CONTRACT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 02 created a single TP10/SL5 contract but blocked because daily market-stop/session entries were treated too strictly as missing M5 entry opens.

02B fixes two issues:

1. Session-boundary missing M5 entry opens are classified as expected non-tradable session exclusions, not data failure.
2. TP/SL is expanded into a fixed USD price-distance grid, including larger targets for volatile GOLD# moves.

This is still contract-only. It does not evaluate outcomes, build features, explore candidates, or generate signals.

## Unit rule

TP/SL are **XAUUSD/GOLD# price-distance USD values**, not pips.

```text
LONG entry 3300.00, TP100 means TP price 3400.00.
LONG entry 3300.00, SL40 means SL price 3260.00.
SHORT entry 3300.00, TP100 means TP price 3200.00.
SHORT entry 3300.00, SL40 means SL price 3340.00.
```

Never interpret these as pips.

## Source inputs

Use only GOLD V3 outputs:

```text
Files/FX_OUTPUTS/gold_v3/01b_candle_gap_session_policy_audit/gold_v3_01b_summary.json
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_m15.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_m5.csv
```

Required 01B status:

```text
GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY
```

## Entry rule

```text
feature_timeframe = M15 closed bar
entry_time_utc = feature_bar_open_utc + 15 minutes
entry_price_source = native M5 open at entry_time_utc
```

If `entry_time_utc` has no native M5 open, classify as:

```text
expected_session_or_market_stop_entry_exclusion
```

Do not shift entry to the next M5 bar.

## Direction expansion

Each eligible base entry produces both directions:

```text
LONG
SHORT
```

## TP/SL grid

Fixed initial grid:

```text
USDPRICE_TP10_SL5_H28
USDPRICE_TP20_SL10_H28
USDPRICE_TP30_SL10_H32
USDPRICE_TP50_SL20_H48
USDPRICE_TP80_SL30_H64
USDPRICE_TP100_SL40_H96
USDPRICE_TP120_SL50_H96
USDPRICE_TP150_SL60_H128
```

Where `Hxx` means horizon in M15 bars.

```text
H28  = 420 minutes
H32  = 480 minutes
H48  = 720 minutes
H64  = 960 minutes
H96  = 1440 minutes
H128 = 1920 minutes
```

## Output row rules

Each contract row includes:

```text
profile_id
strategy_id
price_distance_unit
feature_bar_open_utc
entry_time_utc
direction
entry_price
tp_price_distance_usd
sl_price_distance_usd
tp_price
sl_price
horizon_m15_bars
horizon_minutes
horizon_end_utc
same_bar_priority
outcome
```

`outcome` must be:

```text
NOT_EVALUATED_CONTRACT_ONLY
```

No future hit/outcome/profit may be calculated in 02B.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/02b_label_grid_contract_audit_only/
```

Output files:

```text
GOLD_V3_02B_LABEL_GRID_CONTRACT_AUDIT_ONLY_REPORT.md
gold_v3_02b_summary.json
gold_v3_02b_input_inventory.csv
gold_v3_02b_tp_sl_profile_grid.csv
gold_v3_02b_base_entry_universe.csv
gold_v3_02b_entry_grid_contract_only.csv
gold_v3_02b_excluded_base_entries.csv
gold_v3_02b_excluded_profile_entries.csv
gold_v3_02b_audit_summary.csv
gold_v3_02b_decision_matrix.csv
gold_v3_02b_blocker_matrix.csv
```

ZIP output is disabled.

## Status names

If inputs are missing or 01B is not ready:

```text
GOLD_V3_02B_LABEL_GRID_CONTRACT_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If no eligible base entries or no contract rows are created:

```text
GOLD_V3_02B_LABEL_GRID_CONTRACT_BLOCKED_AUDIT_ONLY
```

If grid contract rows are created and all outcomes remain not evaluated:

```text
GOLD_V3_02B_LABEL_GRID_CONTRACT_READY_WITH_SESSION_EXCLUSIONS_AUDIT_ONLY
```

## Guardrails

- GOLD V3 only.
- Do not read or reuse GOLD V2 selected/source/final/arbitration artifacts.
- TP/SL are GOLD# USD price-distance values, not pips.
- Session gaps are exclusions; entries must not be shifted.
- No features.
- No evaluated labels or outcomes.
- No candidate exploration.
- No signals.
- No ZIP output.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- NO_SIGNAL must not notify Discord.
