# GOLD V3 02 label contract audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_02_LABEL_CONTRACT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 01B approved native candle use with guardrails:

```text
status = GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY
native_candle_use_allowed = true
m1_label_gap_guard_required = true
reconstruct_h4_from_h1_allowed = false
reconstruct_d1_from_h4_allowed = false
```

GOLD V3 02 fixes the initial label contract and entry universe without evaluating outcomes. It must not create win/loss labels, features, signals, candidates, or live logic.

This step exists to prevent the V2 failure mode where future profit/extension was used as selection logic.

## Source-of-truth inputs

Use only GOLD V3 outputs:

```text
Files/FX_OUTPUTS/gold_v3/01b_candle_gap_session_policy_audit/gold_v3_01b_summary.json
Files/FX_OUTPUTS/gold_v3/01b_candle_gap_session_policy_audit/gold_v3_01b_data_use_policy_matrix.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_m15.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_m5.csv
```

Required 01B upstream status:

```text
GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY
```

## Initial default label contract

The first clean V3 label contract is deliberately simple and fixed. It is not optimized.

Important unit clarification:

```text
TP/SL unit = XAUUSD price-distance USD, not pips.
TP 10.0 means entry_price +/- 10.0 on the GOLD# price scale.
SL 5.0 means entry_price -/+ 5.0 on the GOLD# price scale.
Example LONG entry 3300.00 => TP 3310.00, SL 3295.00.
```

```text
strategy_id = GOLD_V3_LABEL_BASE_M15_CLOSE_M5_FIRST_TOUCH_USDPRICE_TP10_SL5_H28_V1
entry_time = feature_bar_open_utc + 15 minutes
feature_timeframe = M15 closed bar
execution/evaluation timeframe = native M5
entry_price_source = native M5 open at entry_time
directions = LONG, SHORT
TP price distance = 10.0 USD on XAUUSD/GOLD# price scale
SL price distance = 5.0 USD on XAUUSD/GOLD# price scale
horizon_m15_bars = 28
horizon_minutes = 420
same_bar_priority = SL_FIRST
outcome = NOT_EVALUATED_CONTRACT_ONLY in this step
AI API = not called
ZIP output = disabled
```

Direction-specific target prices:

```text
LONG:  tp_price = entry_price + 10.0, sl_price = entry_price - 5.0
SHORT: tp_price = entry_price - 10.0, sl_price = entry_price + 5.0
```

## Entry universe rules

For every M15 bar:

```text
feature_bar_open_utc = M15 open time
entry_time_utc = feature_bar_open_utc + 15 minutes
```

Eligibility checks:

```text
entry_time_utc must exist as a native M5 open
horizon_end_utc = entry_time_utc + 420 minutes must be <= last native M5 time
M5 rows must exist in the evaluation window [entry_time_utc, horizon_end_utc]
```

Each eligible entry generates two contract-only rows:

```text
LONG
SHORT
```

No future hit/outcome/profit field is calculated in 02.

## Expected counts

From Phase 00/01 canonical inventory:

```text
M15 rows = 23563
M5 rows = 70684
maximum raw direction rows before lookahead filtering = 23563 * 2 = 47126
```

The exact eligible count is computed by the script and recorded in:

```text
gold_v3_02_label_contract_audit_summary.csv
gold_v3_02_summary.json
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/02_label_contract_audit_only/
```

Output files:

```text
GOLD_V3_02_LABEL_CONTRACT_AUDIT_ONLY_REPORT.md
gold_v3_02_summary.json
gold_v3_02_input_inventory.csv
gold_v3_02_label_contract.json
gold_v3_02_label_contract_audit_summary.csv
gold_v3_02_entry_universe_contract_only.csv
gold_v3_02_excluded_entry_times.csv
gold_v3_02_decision_matrix.csv
gold_v3_02_blocker_matrix.csv
```

ZIP output is disabled by user request. GOLD V3 scripts must not create zip packages unless explicitly requested.

## Audit method

The script must print and write:

```text
source rows: M15 row count, M5 row count
entry universe rows before direction expansion
contract rows after LONG/SHORT expansion
excluded entries by reason
strategy_id count
entry_time uniqueness count
direction counts
outcome value counts
AI API called = false
ZIP output created = false
```

## Status names

If 01B inputs are missing or upstream status fails:

```text
GOLD_V3_02_LABEL_CONTRACT_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If M15/M5 rows are present but eligibility checks produce no entries or missing M5 entry opens are material:

```text
GOLD_V3_02_LABEL_CONTRACT_BLOCKED_AUDIT_ONLY
```

If contract-only entry universe is created and no outcomes/features/signals are generated:

```text
GOLD_V3_02_LABEL_CONTRACT_READY_AUDIT_ONLY
```

## Guardrails

- GOLD V3 only.
- Do not read or reuse GOLD V2 selected/source/final/arbitration artifacts.
- TP/SL are XAUUSD USD price-distance values, not pips.
- No features.
- No evaluated labels or outcomes.
- No candidate exploration.
- No signals.
- No ZIP output unless explicitly requested.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- NO_SIGNAL must not notify Discord.
