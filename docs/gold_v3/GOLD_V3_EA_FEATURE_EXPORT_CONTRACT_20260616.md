# GOLD V3 EA feature export contract

Date: 2026-06-16
Status: implementation contract for EA-side optional feature export
Scope: reduce Python runtime work and live/backtest timestamp drift by letting the MT5 EA export selected closed-candle features in addition to OHLC.

## Why this exists

The current EA exports candle CSV only:

```text
time,open,high,low,close,tick_volume,spread,real_volume
```

This is enough to recompute indicators in Python, but GOLD V3 live bridge needs several derived fields used by the Stage169/170 parallel bucket contract.

If these fields are exported by EA at each closed bar, Python can avoid recalculating large HTF windows on every cycle and can focus on the GOLD V3 bucket contract.

## Non-negotiable CSV rule

The exported latest row must be a closed candle row.

```text
open/as-of row is prohibited
forming candle is prohibited
```

This follows the GOLD V3 CSV contract.

## Recommended file names under MQL5/Files

Keep OHLC files as-is:

```text
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

Add optional lightweight feature snapshots:

```text
gold_v3_m15_feature_snapshot.csv
gold_v3_h1_feature_snapshot.csv
gold_v3_d1_feature_snapshot.csv
gold_v3_live_feature_snapshot.csv
```

The most useful single file is:

```text
gold_v3_live_feature_snapshot.csv
```

One row per latest closed M15 decision bar.

## Minimal single-file export schema

`gold_v3_live_feature_snapshot.csv` should contain at least:

```text
entry_dt
symbol
m15_open
m15_high
m15_low
m15_close
m15_tick_volume
m15_rsi14
h1_close_time
h1_open
h1_high
h1_low
h1_close
h1_atr14
h1_range_atr
h1_up
d1_close_time
d1_open
d1_high
d1_low
d1_close
d1_atr14
d1_dist_atr
exported_at
is_closed
```

Recommended values:

```text
entry_dt: latest closed M15 bar time
h1_close_time: latest closed H1 bar time used for the M15 row
d1_close_time: latest closed D1 bar time used for the M15 row
is_closed: true only if all referenced bars are closed
```

## Feature definitions

These definitions must be frozen before live use.

### m15_rsi14

```text
RSI(14) on M15 close, latest closed M15 row
```

### h1_atr14

```text
ATR(14) on H1 closed candles
```

### h1_range_atr

```text
(H1 high - H1 low) / H1 ATR14
```

### h1_up

Initial practical proxy:

```text
H1 close > previous closed H1 close
```

If historical GOLD V3 used a different H1 trend definition, this must be replaced by the original definition before final live parity.

### d1_atr14

```text
ATR(14) on D1 closed candles
```

### d1_dist_atr

Initial practical proxy:

```text
(M15 close - D1 close reference) / D1 ATR14
```

The exact D1 reference used by historical GOLD V3 must be reconciled before final live parity. Stage169/170 candidate thresholds depend on this value.

## Candidate masks using exported features

With these exported features, Python can evaluate most later candidates:

```text
P1_D1:
  d1_dist_atr <= -1.641755654337

P3_RSI:
  m15_rsi14 >= 73.861004

P4_H1_D1_STRICT:
  h1_range_atr <= 0.737217834712
  d1_dist_atr <= -0.781481

P5_H1UP_CUR:
  h1_up == true
  d1_dist_atr <= 1.247038
  h1_range_atr <= 0.744978
```

The following still need policy-row generation or an equivalent frozen live implementation:

```text
CURRENT:
  policy_key == density_safe||100||Q0.6
  score-desc top 10

P2_DEN:
  policy_key == density_safe||100||Q0.35
  d1_dist_atr <= -0.781481
```

## Optional EA-side policy export

If the EA or a companion script can export policy rows, add:

```text
gold_v3_live_policy_rows.csv
```

Recommended schema:

```text
entry_dt
policy_key
side
score
candidate_source
m15_close
sl_price
tp_price
m15_rsi14
h1_range_atr
h1_up
d1_dist_atr
is_closed
```

If this file exists, Python can apply Stage170 exactly:

```text
CURRENT bucket: density_safe||100||Q0.6, top 10 by score
LATER bucket: P1/P2/P3/P4/P5, one per candidate
conflict policy: skip all on current/later opposite-side conflict
```

## Performance recommendation

Best practical split:

```text
EA:
  export OHLC + lightweight indicators from closed bars

Python:
  apply GOLD V3 contract, conflict logic, payload generation, audit logs
```

Do not implement the whole GOLD V3 contract in EA first. Keep the trading contract in Python so it remains auditable and versioned.

## EX5 note

A compiled `.ex5` cannot be safely modified as source. EA changes require the `.mq5` source file.

If only `.ex5` is available, keep using OHLC export and build the feature snapshot in Python.

## Next stages

```text
174: OHLC + optional EA feature export input audit
175: feature snapshot builder/reconciler
176: policy row reconstruction or policy-row input contract
177: GOLD V3 payload dry-run using existing sender-compatible schema
178: strict7 loop reuse for GOLD V3 demo path
```
