# GOLD V2 CoreA / CoreB RR125 overlap policy

Created: 2026-06-03
Status: audit-only policy definition

## Adopted candidate structure

```text
HIGH_A:
  CoreA = fold4_rules + ABC entry gate + CAP5 sizing

HIGH_B candidate:
  CoreB = RR125_BUY_CONFLUENCE
  Source rules: BUY rules originally selected at RR1.0
  Synthetic TP = 1.25 * SL
  same_count >= 15
  CAP3 sizing
```

CoreA Reject add-ons remain as MEDIUM candidates, not as true CoreB:

```text
RANGE96_REFINED
VOL_TRMEAN32_REFINED
TIER2_HVT
ORIGIN010_REFINED as WATCH/MEDIUM optional
```

## Runtime overlap idea

CoreA and CoreB can overlap on the same entry time.

Suggested initial live/audit interpretation:

```text
CoreA standalone:
  lot_multiplier = 1.0

CoreB standalone:
  lot_multiplier = 1.0

CoreA BUY + CoreB BUY same entry time:
  signal_priority = HIGH_CONFLUENCE
  start with extra CoreB exposure = 0.5
  effective profit audit = CoreA profit + 0.5 * CoreB profit

Future candidate after audit:
  extra CoreB exposure = 1.0
```

Do not use blind double lot immediately. Compare extra 0.5 vs extra 1.0 first.

CoreB is BUY-only in the current RR125 probe. If CoreA SELL and CoreB BUY conflict at exact same time, CoreA should be preferred and CoreB should be skipped until conflict behaviour is separately audited.

## Current overlap audit result

Using:

```text
CoreB = RR125_from_RR1_rules + same_count>=15 + CAP3
```

Aggregate:

| Dataset | View | Count | WR | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025 | CoreA | 200 | 65.50% | 2.38 | +230.24R | -5R | 16.2R | 5 |
| 2025 | CoreB RR125 | 104 | 72.12% | 3.44 | +143.02R | -3R | 7.5R | 4 |
| 2025 | CoreA + CoreB dedup, no extra on overlap | 297 | 67.34% | 2.59 | +353.76R | -5R | 19.2R | 6 |
| 2025 | CoreA + CoreB, extra 0.5 on overlap | 297 | 67.34% | 2.62 | +363.51R | -5R | 19.2R | 6 |
| 2025 | CoreA + CoreB, extra 1.0 on overlap | 297 | 67.34% | 2.66 | +373.26R | -5R | 19.2R | 6 |
| 2026 | CoreA | 125 | 73.60% | 3.80 | +193.50R | -5R | 7.0R | 2 |
| 2026 | CoreB RR125 | 21 | 80.95% | 5.15 | +40.50R | -3R | 6.0R | 2 |
| 2026 | CoreA + CoreB dedup, no extra on overlap | 145 | 74.48% | 3.95 | +232.50R | -5R | 7.0R | 2 |
| 2026 | CoreA + CoreB, extra 0.5 on overlap | 145 | 74.48% | 3.96 | +233.25R | -5R | 7.0R | 2 |
| 2026 | CoreA + CoreB, extra 1.0 on overlap | 145 | 74.48% | 3.97 | +234.00R | -5R | 7.0R | 2 |

Exact same-time same-direction overlap count:

```text
2025: 7 overlaps, all BUY+BUY, WR 85.71%, PF 13.00, CoreA-only overlap profit +24.0R
2026: 1 overlap, BUY+BUY, win
```

## Interpretation

CoreB RR125 can be promoted from WATCH to adopted CoreB candidate.

The overlap itself is high quality, but the overlap sample is small. Therefore:

```text
Adopt CoreB standalone at lot 1.0 in audit/demo.
Adopt CoreA+CoreB confluence at extra CoreB exposure 0.5 first.
Keep extra 1.0 as an audit comparison, not initial live default.
```

## Implementation added

```text
scripts/gold_v2_runtime/evaluate_gold_v2_coreA_coreB_rr125_overlap_audit_only.py
scripts/gold_v2_runtime/bat/02_RUN_COREA_COREB_RR125_OVERLAP_AUDIT_ONLY.bat
```

Default input folders:

```text
Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs
Files\FX_OUTPUTS\gold_v2_rr125_second_core_probe_outputs
```

Default output folder:

```text
Files\FX_OUTPUTS\gold_v2_coreA_coreB_rr125_overlap_audit_only
```

This is still audit-only. It does not connect to Discord or MT5 live trading.
