# GOLD V3 clean re-exploration plan

Created: 2026-06-09

Status: `GOLD_V3_CLEAN_REEXPLORATION_PLAN_READY_AUDIT_ONLY`

## Why GOLD V3 exists

GOLD V2 CoreA/CoreB/MEDIUM remains audit-only and live blocked. The V2 chain found evidence that selected/final/source artifacts may depend on future outcome, profit, time/id keys, and historical source-of-truth artifacts.

GOLD V3 is a clean re-exploration track. It must not reuse V2 selected rows, final SOT rows, representative profit bindings, arbitration outputs, or top-profit-derived source recovery logic.

## Required separation from V2

Repository paths:

```text
docs/gold_v3/
scripts/gold_v3_runtime/
scripts/gold_v3_runtime/bat/
configs/gold_v3/
```

Local data/output paths under MT5 Files root:

```text
Files/FX_INPUTS/gold_v3/raw_candles/
Files/FX_OUTPUTS/gold_v3/
Files/FX_OUTPUTS/gold_v3/_run_index/
Files/FX_OUTPUTS/gold_v3/_archive/
```

V2 outputs must not be mixed into V3 outputs. Existing V2 output folders are not deleted by V3 scripts. Optional V2 quarantine/move scripts must be dry-run by default.

## Uploaded candle sets

The current user-provided candle sets are:

### GOLD# 2025 MT5 export

Use as the first GOLD V3 primary 2025 research SOT candidate because it includes UTC/JST fields and fetch metadata.

```text
gold#_m1.csv
gold#_m5.csv
gold#_m15.csv
gold#_h1.csv
gold#_h4.csv
gold#_d1.csv
fetch_summary.json
```

Expected from uploaded fetch_summary:

```text
symbol_used = GOLD#
period = 2025-01-01 UTC to 2026-01-01 UTC
M1 rows = 353074
M5 rows = 70684
M15 rows = 23563
H1 rows = 5894
H4 rows = 1541
D1 rows = 258
```

### goldsharp long/reference set

Use only as auxiliary or extended-history reference until reconciled with GOLD# symbol/session/time conventions.

```text
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

## Non-negotiable V3 rules

### 1. Future labels are allowed only as labels

A future move, TP/SL result, MFE/MAE, max favorable excursion, exit_time, or realized profit may be used to create labels/evaluation outcomes only.

They must not appear in feature columns or live selection columns.

### 2. Candidate discovery must be train-only

For every walk-forward fold:

```text
train period: discover candidates and thresholds
validation period: tune candidate selection if needed
test/holdout period: evaluate only, no candidate selection
```

No candidate or rule may be selected based on holdout profit.

### 3. No “伸びた場所 first, then mimic” shortcut for live SOT

It is acceptable to define positive labels as future extension. It is not acceptable to first locate large future moves and then promote their surrounding features as SOT without train-only validation.

### 4. No top-profit representative binding

Do not select live rules by:

```text
top_profit
selected_profit_r
best_profit
max_profit
exit_time
top_exit_time
winner row
final_sot after outcome comparison
```

### 5. Backtest/live parity first

GOLD V3 must build a single evaluator contract used by both backtest and later paper/live evaluation. No separate approximate live reimplementation.

### 6. V3 external actions remain OFF

Until explicitly approved:

```text
Discord OFF
MT5 orders OFF
AI API OFF
live hook OFF
live evaluator OFF
final signal OFF
```

NO_SIGNAL must not notify Discord.

## Initial phases

### Phase 00: Workspace and candle inventory

Create separated V3 directories, inventory candle files, and write source selection matrix. No feature engineering and no signals.

### Phase 01: Candle normalization and time audit

Normalize GOLD# primary candles into a canonical schema. Audit M1/M5/M15/H1/H4/D1 alignment and HTF open-time convention before any features.

### Phase 02: Label contract

Define future labels only after time audit. Candidate examples:

```text
M15 entry
M5 or M1 intrabar evaluation
TP/SL first-touch with SL-priority on same bar
fixed USD labels, not ATR-dependent until explicitly tested
```

### Phase 03: Entry-time features only

Build features from candles whose open/close availability is unambiguous at the entry decision time. HTF features must be asof-joined using only closed or explicitly allowed bars.

### Phase 04: Walk-forward candidate exploration

Candidate rules are discovered inside train folds only. Holdout metrics are recorded but cannot alter rules.

### Phase 05: Paper/live audit-only evaluator

Only after backtest/live parity and no-leakage audits pass.

## Initial success criteria

Phase 00 is successful if:

```text
V3 folders are created.
Candle inventory is written.
GOLD# and goldsharp sets are classified separately.
No V2 files are modified/deleted.
No signals are generated.
No external action is performed.
```

## Current status

```text
GOLD_V3 = planning / workspace setup only
GOLD_V2 = quarantined historical research, live blocked
```
