# GOLD V3 parallel demo reuse patch guide

Date: 2026-06-16
Status: design / patch guide
Scope: reuse the existing GOLD strict7 guarded demo payload/sender structure, replacing only the signal source with GOLD V3 parallel bucket candidates.

## Existing files reviewed from local upload

- `run_gold_strict_7_guarded_demo_autotrade_forever_aligned.py`
  - outer forever loop
  - calls `scripts/gold_strict_7_signals/run_gold_strict_7_guarded_demo_autotrade_from_csv.py`
- `run_gold_strict_7_guarded_demo_autotrade_from_csv.py`
  - reads live GOLD CSVs
  - detects strict7 signals
  - builds sender-compatible payload CSV
  - calls `scripts/send_mt5_order_from_payload.py`
- `send_mt5_order_from_payload.py`
  - thin wrapper around `_send_mt5_order_from_payload_original.py`
  - patches allow-any behavior so same active magic is blocked
- `_send_mt5_order_from_payload_original.py`
  - existing guarded sender
  - default dry-run/check-only
  - duplicate `order_key` prevention
  - expected-login guard
  - demo-account guard
  - open-position policy guard
  - detailed CSV/JSON reports

## Core decision

Do not rewrite the existing guarded sender.

Reuse:

- payload schema
- duplicate key ledger
- expected login check
- demo account guard
- position policy guard
- detailed sender report outputs

Replace:

- strict7 imports
- strict7 signal specs
- strict7 candidate detector
- strict7 TP/SL profile mapping
- strict7 strategy ids and magic numbers
- strict7 one-order defaults

## GOLD V3 parallel contract to map into payloads

Selected variant:

```text
PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT
```

Buckets:

```text
CURRENT bucket:
  policy_key = density_safe||100||Q0.6
  selector = score desc
  max units = 10
  lot per unit = 0.01

LATER bucket:
  P1_D1
  P2_DEN
  P3_RSI
  P4_H1_D1_STRICT
  P5_H1UP_CUR
  one unit per candidate
  max units = 5
  lot per unit = 0.01
```

Conflict rules:

```text
- mixed LONG/SHORT inside current bucket -> skip current bucket
- mixed LONG/SHORT inside later bucket -> skip later bucket
- current bucket and later bucket opposite directions at the same timestamp -> skip all units at that timestamp
```

Maximum planned dry-run/demo exposure if all units appear:

```text
max units = 15
max lot = 0.15
```

## Candidate masks to implement in the copied wrapper

The copied wrapper should not read old strict7 signal specs.

Expected live candidate/features columns:

```text
entry_dt or close_time
policy_key
side or direction
close or entry_price_reference
score or feature_score
sl_price and tp_price, or enough columns to calculate them safely
m15_rsi14
d1_dist_atr
h1_range_atr
h1_up
```

Candidate filters:

```text
CURRENT:
  policy_key == density_safe||100||Q0.6

P1_D1:
  policy_key != density_safe||100||Q0.6
  d1_dist_atr <= -1.641755654337

P2_DEN:
  policy_key == density_safe||100||Q0.35
  d1_dist_atr <= -0.781481

P3_RSI:
  policy_key != density_safe||100||Q0.6
  m15_rsi14 >= 73.861004

P4_H1_D1_STRICT:
  policy_key != density_safe||100||Q0.6
  h1_range_atr <= 0.737217834712
  d1_dist_atr <= -0.781481

P5_H1UP_CUR:
  policy_key != density_safe||100||Q0.6
  h1_up == true
  d1_dist_atr <= 1.247038
  h1_range_atr <= 0.744978
```

## Files to create by copying old strict7 structure

Suggested new paths:

```text
scripts/gold_v3_runtime/run_gold_v3_parallel_guarded_demo_from_csv.py
scripts/gold_v3_runtime/run_gold_v3_parallel_guarded_demo_forever_aligned.py
scripts/gold_v3_runtime/bat/run_gold_v3_parallel_guarded_demo_forever_aligned.bat
```

## Exact replacement map

In the copied `from_csv` wrapper, replace this strict7 block:

```text
validate_signal_specs()
specs = get_signal_specs()
ctx = load_context(paths, args)
signals = collect_recent_signals(ctx, specs, args)
payloads = [payload_row(row, spec, args, rank=i + 1) for i, (_, spec, row) in enumerate(signals)]
```

with GOLD V3 equivalents:

```text
ctx = load_gold_v3_live_candidates(args)
signals = collect_gold_v3_parallel_signals(ctx, args)
payloads = [gold_v3_payload_row(sig, args, rank=i + 1) for i, sig in enumerate(signals)]
```

## Sender settings for GOLD V3 demo path

Old strict7 defaults are intentionally conservative:

```text
max-orders = 1
max-symbol-positions = 1
max-symbol-lot = 0.01
position-policy = block_any
```

GOLD V3 parallel bucket needs:

```text
max-orders = 15
max-symbol-positions = 15
max-symbol-lot = 0.15
position-policy = allow_same_direction
lot = 0.01
```

Rationale:

- GOLD V3 itself handles same-timestamp opposite-side conflicts before payload creation.
- Sender should still block opposite live positions using `allow_same_direction`.
- Use distinct magic numbers per bucket/candidate to let the existing same-magic protection work.

Suggested magic number map:

```text
CURRENT_CAP10:      27017410
P1_D1:              27017401
P2_DEN:             27017402
P3_RSI:             27017403
P4_H1_D1_STRICT:    27017404
P5_H1UP_CUR:        27017405
```

## Operational notes

1. First run copied wrapper without final demo-send flags.
2. Confirm payload CSV rows, sides, lots, magic numbers, SL/TP.
3. Confirm sender report returns check-ok rows and no validation errors.
4. Only then use the old demo-send flag pattern manually.
5. Keep existing order ledger separate from strict7 ledger:

```text
data/runtime_state/gold/gold_v3_parallel/guarded_demo_order_ledger.csv
```

## Do not mix old signal logic

Old strict7 logic may be reused only as infrastructure shape.

Do not reuse strict7 signal conditions, strict7 candidate specs, or strict7 detector as GOLD V3 trading logic.

## Current blocker before actual copied wrapper

The copied wrapper requires a live GOLD V3 candidate/features CSV source. If that CSV does not yet exist, first build a feature/candidate snapshot writer that produces the required columns from the latest closed row only.
