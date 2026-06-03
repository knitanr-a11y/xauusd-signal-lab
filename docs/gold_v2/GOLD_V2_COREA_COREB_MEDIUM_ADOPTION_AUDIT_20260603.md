# GOLD V2 CoreA + CoreB + MEDIUM adoption audit

Created: 2026-06-03
Status: audit-only / adoption candidate

## Adopted hierarchy

```text
HIGH_A:
  CoreA = fold4_rules + ABC entry gate + CAP5 sizing

HIGH_B:
  CoreB = RR125_BUY_CONFLUENCE
  Source rules: BUY rules originally selected at RR1.0
  Synthetic TP = 1.25 * SL
  same_count >= 15
  CAP3 sizing

HIGH_CONFLUENCE:
  CoreA BUY + CoreB BUY exact same entry time
  Initial extra CoreB exposure = 0.5

MEDIUM:
  RANGE96_REFINED
  VOL_TRMEAN32_REFINED
  TIER2_HVT
```

ORIGIN010_REFINED remains WATCH and is not included in the default MEDIUM set.

## Precedence

```text
CoreA/CoreB > MEDIUM
```

If MEDIUM has the same entry_time as CoreA/CoreB, MEDIUM is skipped.

If multiple MEDIUM signals share the same entry_time + direction, keep one by priority:

```text
RANGE96_REFINED > VOL_TRMEAN32_REFINED > TIER2_HVT
```

## Latest audit result

CoreA + CoreB without MEDIUM:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 297 | 67.34% | 2.62 | +363.51R | -5R | 19.2R |
| 2026 | 145 | 74.48% | 3.96 | +233.25R | -5R | 7.0R |

CoreA + CoreB + MEDIUM:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 346 | 69.08% | 2.84 | +439.51R | -5R | 19.2R |
| 2026 | 183 | 72.13% | 3.65 | +248.75R | -5R | 7.0R |

## Interpretation

MEDIUM improves 2025 materially:

```text
+49 trades
+76.00R
WR +1.74 percentage points
PF +0.22
MaxDD unchanged
```

MEDIUM increases 2026 total R and count but dilutes WR/PF moderately:

```text
+38 trades
+15.50R
WR -2.35 percentage points
PF -0.31
MaxDD unchanged
```

This is acceptable if MEDIUM remains lower priority and does not replace HIGH signals.

## Source breakdown after deduplication

2025:

| Source | Count | WR | PF | TotalR |
|---|---:|---:|---:|---:|
| CoreA only | 193 | 64.77% | 2.25 | +206.24R |
| CoreA+CoreB confluence | 7 | 85.71% | 10.64 | +33.75R |
| CoreB only | 97 | 71.13% | 3.22 | +123.52R |
| MEDIUM_RANGE96_REFINED | 21 | 80.95% | 5.86 | +34.00R |
| MEDIUM_VOL_TRMEAN32_REFINED | 16 | 75.00% | 3.71 | +19.00R |
| MEDIUM_TIER2_HVT | 12 | 83.33% | 24.00 | +23.00R |

2026:

| Source | Count | WR | PF | TotalR |
|---|---:|---:|---:|---:|
| CoreA only | 124 | 73.39% | 3.78 | +191.50R |
| CoreA+CoreB confluence | 1 | 100.00% | inf | +2.75R |
| CoreB only | 20 | 80.00% | 5.00 | +39.00R |
| MEDIUM_RANGE96_REFINED | 30 | 66.67% | 2.32 | +14.50R |
| MEDIUM_VOL_TRMEAN32_REFINED | 7 | 57.14% | 1.67 | +2.00R |
| MEDIUM_TIER2_HVT | 1 | 0.00% | 0.00 | -1.00R |

## Implementation added

```text
scripts/gold_v2_runtime/evaluate_gold_v2_coreA_coreB_medium_audit_only.py
scripts/gold_v2_runtime/bat/03_RUN_COREA_COREB_MEDIUM_AUDIT_ONLY.bat
```

Default input folders:

```text
Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs
Files\FX_OUTPUTS\gold_v2_rr125_second_core_probe_outputs
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs
```

Default output folder:

```text
Files\FX_OUTPUTS\gold_v2_coreA_coreB_medium_audit_only
```

Still audit-only. No live order execution, AI API calls, Discord, or MT5 integration.
