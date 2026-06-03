# GOLD V2 RR1.25 second Core probe

Created: 2026-06-03
Status: audit-only / synthetic RR re-evaluation

## Purpose

Existing second-Core RR bucket comparison had only RR1.0, RR1.5, and RR2.0. RR1.25 did not exist in the selected-rules universe.

This probe synthetically re-evaluates RR1.25 by keeping each selected BUY rule entry condition and SL distance, then setting:

```text
TP = 1.25 * SL
RR = 1.25
```

Two source groups were evaluated:

```text
RR125_from_RR1_rules:
  only BUY rules originally selected at RR1.0

RR125_from_ALL_BUY_rules:
  all selected BUY rules, regardless of original RR
```

Core A remains:

```text
Core A = fold4_rules + ABC + CAP5
```

## Best RR1.25 candidate

Best practical candidate:

```text
RR125_from_RR1_rules
AND same_count >= 15
CAP3
```

Standalone:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 104 | 72.12% | 3.44 | +143.02R | -3R | 7.5R |
| 2026 | 21 | 80.95% | 5.15 | +40.50R | -3R | 6.0R |

Core A + RR1.25 candidate:

| Dataset | Count | WR | PF | TotalR |
|---|---:|---:|---:|---:|
| 2025 | 297 | 67.00% | 2.56 | +351.51R |
| 2026 | 138 | 74.64% | 4.02 | +226.50R |

A stricter variant:

```text
RR125_from_RR1_rules
AND same_count >= 15
AND unique_origins >= 2
CAP3
```

Standalone:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 86 | 70.93% | 3.55 | +120.65R | -3R | 4.54R |
| 2026 | 16 | 87.50% | 10.40 | +35.25R | -3R | 3.0R |

Core A + strict RR1.25 candidate:

| Dataset | Count | WR | PF | TotalR |
|---|---:|---:|---:|---:|
| 2025 | 280 | 66.43% | 2.55 | +332.89R |
| 2026 | 133 | 75.19% | 4.21 | +221.25R |

## Interpretation

RR1.25 is clearly worth exploring.

Compared with the prior broad BUY RR1.0 candidate:

```text
BUY RR1.0 broad:
  2025: 623 / WR 56.02% / PF 1.43 / +211.34R
  2026: 119 / WR 63.87% / PF 1.94 / +49.0R
```

RR1.25 with same_count>=15 is much cleaner:

```text
RR1.25 refined:
  2025: 104 / WR 72.12% / PF 3.44 / +143.02R
  2026: 21 / WR 80.95% / PF 5.15 / +40.50R
```

This still may not be a full second Core because 2026 count is only 21, but it is much stronger than the earlier RR1.0/1.5/2.0 broad buckets.

## Recommendation

Promote RR1.25 refined to the candidate list as MEDIUM/HIGH-watch:

```text
RR125_BUY_CONFLUENCE:
  Source rules: BUY rules originally selected at RR1.0
  TP = 1.25 * SL
  same_count >= 15
  CAP3
```

More conservative option:

```text
RR125_BUY_CONFLUENCE_STRICT:
  Source rules: BUY rules originally selected at RR1.0
  TP = 1.25 * SL
  same_count >= 15
  unique_origins >= 2
  CAP3
```

Next step should be a formal evaluator that compares:

```text
Core A only
Core A + RANGE96_REFINED
Core A + VOL_TRMEAN32_REFINED
Core A + TIER2_HVT
Core A + RR125_BUY_CONFLUENCE
```

All add-ons remain CAP3 until forward validation.
