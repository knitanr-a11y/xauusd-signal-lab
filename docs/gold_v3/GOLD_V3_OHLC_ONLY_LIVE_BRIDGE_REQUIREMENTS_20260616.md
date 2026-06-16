# GOLD V3 OHLC-only live bridge requirements

Date: 2026-06-16
Status: requirements / implementation boundary
Context: the EA exports candle CSV only. No ready-made `policy_key`, `d1_dist_atr`, `h1_range_atr`, `m15_rsi14`, or `h1_up` columns are available from the EA.

## Confirmed uploaded M15 CSV shape

The uploaded `goldsharp_m15.csv` has the candle-only schema:

```text
time,open,high,low,close,tick_volume,spread,real_volume
```

This is enough to compute ordinary indicators, but it is not enough by itself to emit the Stage170 parallel contract because Stage170/169 logic expects derived features and K2 policy rows.

## Required live reconstruction pipeline

The old strict7 live wrapper works because it starts from OHLC and computes its own detector context.

GOLD V3 needs the same style of pipeline:

```text
M1/M5/M15/H1/H4/D1 candle CSVs
  -> normalize closed candle rows
  -> compute indicators/features
  -> build live candidate/policy rows
  -> apply GOLD V3 parallel bucket contract
  -> write payload-compatible candidate rows for the existing guarded sender structure
```

## Inputs needed from EA / MT5 Files

Minimum recommended candle files:

```text
goldsharp_m1.csv   optional but useful for future execution detail
goldsharp_m5.csv   useful for judgment/close confirmation
goldsharp_m15.csv  required base signal timeframe
goldsharp_h1.csv   required for h1_range_atr and h1_up
goldsharp_h4.csv   keep available for context parity / future filters
goldsharp_d1.csv   required for d1_dist_atr
```

Required columns for each candle CSV:

```text
time
open
high
low
close
tick_volume
spread
real_volume
```

The latest row must be treated as closed, consistent with the GOLD V3 CSV contract. No open/as-of shortcut is allowed.

## Derived features that can be computed directly from candle CSVs

These can be computed from OHLC:

```text
m15_rsi14
h1_atr14 / h1_range_atr
h1_up
d1_atr14 / d1_dist_atr
basic direction side if a deterministic candle-only rule is defined
```

For example:

```text
m15_rsi14 = RSI(14) on M15 close
h1_range_atr = (H1 high - H1 low) / H1 ATR14
h1_up = H1 close > H1 previous close or a defined H1 trend proxy
d1_dist_atr = distance of M15 close to D1 reference divided by D1 ATR14
```

The exact reference definition for `d1_dist_atr` must match the historical GOLD V3 feature generator, or live/backtest parity will be weak.

## Features that are not candle indicators by themselves

The current bucket depends on:

```text
policy_key == density_safe||100||Q0.6
score / feature_score for selecting top 10 rows
```

This cannot be obtained from candle CSV alone unless we also port the K2 candidate/policy generator that produced those policy rows historically.

Therefore, there are two possible implementation paths:

### Path A: Full parity path

Rebuild/port the GOLD V3 K2 source candidate generator from OHLC.

Then live can produce:

```text
policy_key
feature_score / score
side
entry_dt
sl_price
tp_price
m15_rsi14
d1_dist_atr
h1_range_atr
h1_up
```

This is the correct path for using both:

```text
CURRENT bucket: density_safe||100||Q0.6
LATER bucket: P1_D1/P2_DEN/P3_RSI/P4_H1_D1_STRICT/P5_H1UP_CUR
```

### Path B: Partial feature-only bridge

Use only later candidates that can be directly computed from OHLC-derived features.

This can cover:

```text
P1_D1
P3_RSI
P4_H1_D1_STRICT
P5_H1UP_CUR
```

But it cannot faithfully cover:

```text
CURRENT bucket density_safe||100||Q0.6
P2_DEN density_safe||100||Q0.35
```

because those need policy_key generation.

Path B is faster but would not match Stage170/169 full selected contract.

## Stage169 logic dependency

The Stage169 audit implementation expects already-built policy/feature rows. It does not create the features from raw candles.

It applies:

```text
CURRENT bucket: policy_norm == density_safe||100||Q0.6, score-desc, top 10
LATER bucket: P1/P2/P3/P4/P5 masks using policy_norm + m15_rsi14 + d1_dist_atr + h1_range_atr + h1_up
```

So for live use, the missing part is not the bucket contract. The missing part is the candle-to-policy-row generator.

## Recommended next implementation order

1. `GOLD_V3_174_OHLC_INPUT_CONTRACT_AUDIT_ONLY`
   - verify all candle CSVs exist
   - verify schema and latest closed row
   - verify no duplicate timestamps
   - verify enough rows for indicators

2. `GOLD_V3_175_OHLC_FEATURE_SNAPSHOT_AUDIT_ONLY`
   - compute M15/H1/D1 features from candle CSVs
   - output latest closed feature snapshot

3. `GOLD_V3_176_K2_POLICY_ROW_RECONSTRUCTION_AUDIT_ONLY`
   - locate/port historical K2 policy-row generation
   - output live candidate/policy rows with policy_key and score

4. `GOLD_V3_177_PARALLEL_BUCKET_PAYLOAD_DRY_RUN`
   - apply Stage170 selected contract to latest live policy rows
   - write sender-compatible payload CSV
   - no forced demo-send flag in the generated BAT

5. `GOLD_V3_178_DEMO_SENDER_LOOP_REUSE`
   - copy old strict7 loop structure
   - point it to GOLD V3 payload wrapper
   - keep existing sender guards and order ledger separation

## Important implementation boundary

Do not mix old strict7 signal logic into GOLD V3.

The old strict7 files may be reused as infrastructure pattern only:

```text
forever loop
payload schema
sender invocation
ledger layout
summary logging
```

The signal logic must come from GOLD V3 reconstructed OHLC features / policy rows.
