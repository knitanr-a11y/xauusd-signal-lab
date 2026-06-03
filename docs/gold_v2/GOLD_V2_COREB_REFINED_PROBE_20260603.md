# GOLD V2 CoreB refined probe

Created: 2026-06-03
Status: audit-only / exploratory

## Purpose

The previous broad CoreB candidates were too weak. This probe refines the three requested candidates:

```text
COREB_ORIGIN010_CAP3
COREB_VOL_TRMEAN32_CAP3
COREB_RANGE96_CAP3
```

Core A remains fixed:

```text
Core A = fold4_rules + ABC + CAP5
```

All CoreB refined candidates are Core A REJECT only and use CAP3 sizing.

## Refined rules

```text
ORIGIN010_REFINED:
  CoreA REJECT
  AND top_candidate_id == GOLDV2_ORIGIN_010
  AND range96 >= 41.99
  AND same_direction_count <= 9
  CAP3

VOL_TRMEAN32_REFINED:
  CoreA REJECT
  AND tr_mean_32 >= 10.867578
  AND ret96 <= -2.725
  AND range96 >= 176.453
  CAP3

RANGE96_REFINED:
  CoreA REJECT
  AND range96 >= 129.6835
  AND trend_eff96 <= 0.355591
  AND top_direction == SELL
  CAP3
```

## Standalone comparison

| Dataset | View | Count | WR | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025_fold4 | CORE_A | 200 | 65.50% | 2.38 | +230.24R | -5R | 16.2R | 5 |
| 2025_fold4 | ORIGIN010_REFINED | 39 | 66.67% | 2.31 | +24.99R | -3R | 12.0R | 4 |
| 2025_fold4 | VOL_TRMEAN32_REFINED | 20 | 75.00% | 4.71 | +26.00R | -2R | 5.0R | 3 |
| 2025_fold4 | RANGE96_REFINED | 21 | 80.95% | 5.86 | +34.00R | -3R | 3.0R | 1 |
| 2025_fold4 | TIER2_HVT | 20 | 80.00% | 6.83 | +35.00R | -3R | 3.0R | 2 |
| 2026_WF | CORE_A | 125 | 73.60% | 3.80 | +193.50R | -5R | 7.0R | 2 |
| 2026_WF | ORIGIN010_REFINED | 13 | 92.31% | 9.00 | +16.00R | -2R | 2.0R | 1 |
| 2026_WF | VOL_TRMEAN32_REFINED | 16 | 75.00% | 3.75 | +11.00R | -1R | 2.0R | 2 |
| 2026_WF | RANGE96_REFINED | 30 | 66.67% | 2.32 | +14.50R | -2R | 4.0R | 3 |
| 2026_WF | TIER2_HVT | 11 | 81.82% | 6.25 | +10.50R | -1R | 2.0R | 2 |

## Core A + refined candidates

| Dataset | View | Count | WR | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025_fold4 | CORE_A_PLUS_ORIGIN010_REFINED | 239 | 65.69% | 2.37 | +255.24R | -5R | 16.2R | 6 |
| 2025_fold4 | CORE_A_PLUS_VOL_TRMEAN32_REFINED | 220 | 66.36% | 2.47 | +256.24R | -5R | 16.2R | 5 |
| 2025_fold4 | CORE_A_PLUS_RANGE96_REFINED | 221 | 66.97% | 2.52 | +264.24R | -5R | 16.2R | 5 |
| 2025_fold4 | CORE_A_PLUS_ALL3_REFINED | 274 | 67.52% | 2.57 | +309.24R | -5R | 16.2R | 6 |
| 2025_fold4 | CORE_A_PLUS_ALL3_REFINED_PLUS_TIER2_HVT | 286 | 68.18% | 2.68 | +332.24R | -5R | 16.2R | 6 |
| 2026_WF | CORE_A_PLUS_ORIGIN010_REFINED | 138 | 75.36% | 3.95 | +209.50R | -5R | 7.0R | 1 |
| 2026_WF | CORE_A_PLUS_VOL_TRMEAN32_REFINED | 141 | 73.76% | 3.80 | +204.50R | -5R | 7.0R | 2 |
| 2026_WF | CORE_A_PLUS_RANGE96_REFINED | 155 | 72.26% | 3.60 | +208.00R | -5R | 7.0R | 2 |
| 2026_WF | CORE_A_PLUS_ALL3_REFINED | 170 | 72.35% | 3.59 | +220.00R | -5R | 7.0R | 2 |
| 2026_WF | CORE_A_PLUS_ALL3_REFINED_PLUS_TIER2_HVT | 171 | 71.93% | 3.55 | +219.00R | -5R | 7.0R | 2 |

## Interpretation

The requested candidates can be improved substantially by filtering.

Raw candidates were weak:

```text
COREB_ORIGIN010_CAP3 raw 2025: WR 55.34% / PF 1.36
COREB_VOL_TRMEAN32 raw 2025: WR 56.52% / PF 1.62
COREB_RANGE96 raw 2025: WR 56.52% / PF 1.53
```

Refined candidates are much better:

```text
ORIGIN010_REFINED 2025: WR 66.67% / PF 2.31
VOL_TRMEAN32_REFINED 2025: WR 75.00% / PF 4.71
RANGE96_REFINED 2025: WR 80.95% / PF 5.86
```

However, they are still not a clean second Core because count is limited and the combined ALL3 version slightly dilutes 2026 win rate compared with Core A alone.

## Recommendation

Do not call them HIGH Core B yet.

Better hierarchy:

```text
HIGH:
  Core A = fold4_rules + ABC + CAP5

MEDIUM:
  RANGE96_REFINED
  VOL_TRMEAN32_REFINED
  TIER2_HVT

WATCH / optional MEDIUM:
  ORIGIN010_REFINED
```

Among the three requested candidates, ranking is:

```text
1. RANGE96_REFINED
2. VOL_TRMEAN32_REFINED
3. ORIGIN010_REFINED
```

A practical next runtime-audit policy could evaluate:

```text
Core A only
Core A + RANGE96_REFINED
Core A + RANGE96_REFINED + VOL_TRMEAN32_REFINED
Core A + RANGE96_REFINED + VOL_TRMEAN32_REFINED + TIER2_HVT
```

Keep all add-ons CAP3 and MEDIUM priority until forward validation.
