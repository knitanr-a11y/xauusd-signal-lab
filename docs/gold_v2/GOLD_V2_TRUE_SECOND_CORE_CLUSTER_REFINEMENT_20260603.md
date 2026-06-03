# GOLD V2 true second Core cluster-level refinement

Created: 2026-06-03
Status: audit-only / exploratory

## Purpose

Refine the two broad true-second-Core candidates by reducing count and increasing WR/PF:

```text
BUY & RR1.0
GOLDV2_ORIGIN_003
```

This pass uses cluster-level confluence filters that are known at signal time:

```text
same_count
unique_origins
```

Core A remains fixed:

```text
Core A = fold4_rules + ABC + CAP5
```

## BUY & RR1.0 refinement

Best practical filter:

```text
BUY & RR1.0
AND same_count >= 3
AND unique_origins >= 2
CAP3
```

Result:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 170 | 66.47% | 2.05 | +120.05R | -3R | 7R |
| 2026 | 12 | 75.00% | 2.43 | +10.0R | -3R | 6R |

Original raw candidate:

| Dataset | Count | WR | PF | TotalR | Worst |
|---|---:|---:|---:|---:|---:|
| 2025 | 623 | 56.02% | 1.43 | +211.34R | -3R |
| 2026 | 119 | 63.87% | 1.94 | +49.0R | -3R |

Interpretation:

```text
The filter greatly improves quality, but 2026 count becomes too small.
It is not yet a second Core. It can be a MEDIUM confluence candidate.
```

## GOLDV2_ORIGIN_003 refinement

Cluster filters can make 2025 look much better, for example:

```text
GOLDV2_ORIGIN_003
AND same_count >= 10
CAP3
```

2025 result:

```text
92 trades / WR 73.91% / PF 3.86 / +115.71R / worst -3R
```

But this leaves 0 trades in 2026. Therefore it is not robust.

The only filter that keeps both 2025 and 2026 alive is weak:

```text
K2 rule subset
AND same_count >= 2
```

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 70 | 61.43% | 2.00 | +47.23R | -3R | 6.63R |
| 2026 | 21 | 57.14% | 1.33 | +6.0R | -2R | 4.0R |

Interpretation:

```text
GOLDV2_ORIGIN_003 can be made attractive on 2025, but those refinements do not carry into 2026.
Do not promote this as Core B.
```

## Recommendation

Keep:

```text
BUY_RR1_CONFLUENCE:
  BUY & RR1.0
  same_count >= 3
  unique_origins >= 2
  CAP3
  priority = MEDIUM / WATCH
```

Reject for true Core B:

```text
GOLDV2_ORIGIN_003 refined variants
```

Reason:

```text
BUY_RR1 refined: quality improves but 2026 count is too small.
ORIGIN003 refined: 2025 can improve, but 2026 robustness is poor.
```

This is useful exploration, but it still does not produce a HIGH-priority second Core.
