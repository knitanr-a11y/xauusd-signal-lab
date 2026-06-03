# GOLD V2 ABC stack-cap validation on 2025 fold4 and 2026 WF

Created: 2026-06-03
Status: audit-only / not runtime approved

## Purpose

The 2025 external validation showed that ABC as an entry gate remains interesting, but unlimited same-direction stacking is unsafe. This audit compares several sizing variants on:

```text
2025: fold4_rules fixed universe, full year
2026: WF TOP2 test universe, 2026-03 to 2026-06 partial
```

ABC entry conditions are frozen. Only the stack sizing changes.

## Definitions

```text
ABC_original_A_uncap:
  A uses all same-direction stacked profit.
  B/C use CAP3.

ABC_CAP3_all_kept:
  A/B/C all use CAP3.

ABC_CAP5_A_BC_CAP3:
  A uses top5 same-direction candidates.
  B/C use CAP3.
  This is also the practical max-loss-about-5R variant.

ABC_origin1_A_BC_CAP3:
  A uses at most one candidate per origin.
  B/C use CAP3.

ABC_origin1_cap5_A_BC_CAP3:
  A uses at most one candidate per origin, capped to top5 origins.
  B/C use CAP3.
```

## 2025 fold4_rules result

| View | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ABC_original_A_uncap | 200 | 63.00% | 2.11 | +466.73R | +2.334R | -43R | 63.38R | 5 |
| ABC_CAP3_all_kept | 200 | 66.00% | 2.33 | +176.24R | +0.881R | -3R | 13.29R | 5 |
| ABC_CAP5_A_BC_CAP3 | 200 | 65.50% | 2.38 | +230.24R | +1.151R | -5R | 16.20R | 5 |
| ABC_origin1_A_BC_CAP3 | 200 | 66.50% | 2.62 | +210.73R | +1.054R | -7R | 13.29R | 5 |
| ABC_origin1_cap5_A_BC_CAP3 | 200 | 66.50% | 2.58 | +201.23R | +1.006R | -5R | 13.29R | 5 |
| baseline_CAP3_all_clusters | 2033 | 53.47% | 1.23 | +399.91R | +0.197R | -3R | 50.09R | 18 |
| baseline_uncap_all_clusters | 2033 | 51.94% | 1.15 | +666.66R | +0.328R | -67R | 288.56R | 18 |

## 2026 WF TOP2 result

| View | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ABC_original_A_uncap | 125 | 74.40% | 4.52 | +225.50R | +1.804R | -5R | 6R | 2 |
| ABC_CAP3_all_kept | 125 | 75.20% | 3.81 | +168.50R | +1.348R | -3R | 4R | 2 |
| ABC_CAP5_A_BC_CAP3 | 125 | 73.60% | 3.80 | +193.50R | +1.548R | -5R | 7R | 2 |
| ABC_origin1_A_BC_CAP3 | 125 | 72.80% | 4.40 | +183.50R | +1.468R | -4R | 6R | 2 |
| ABC_origin1_cap5_A_BC_CAP3 | 125 | 72.80% | 4.01 | +171.50R | +1.372R | -5R | 8R | 2 |
| baseline_CAP3_all_clusters | 351 | 59.26% | 1.89 | +187.00R | +0.533R | -3R | 9R | 4 |
| baseline_uncap_all_clusters | 351 | 58.69% | 1.96 | +227.50R | +0.648R | -11R | 18R | 4 |

## Interpretation

Unlimited A stacking is rejected for runtime:

```text
2025 worst: -43R
2025 MaxDD: 63R
```

CAP3 is the safest sizing. It works on both years and has the lowest tail risk:

```text
2025: +176.24R / PF 2.33 / worst -3R
2026: +168.50R / PF 3.81 / worst -3R
```

CAP5 is the most natural middle ground:

```text
2025: +230.24R / PF 2.38 / worst -5R
2026: +193.50R / PF 3.80 / worst -5R
```

Origin1 variants reduce duplicate-origin stacking, but they are not clearly better than CAP5. Origin1 has a 2025 worst of -7R unless also capped.

## Current recommendation

Use ABC as an entry gate, but not as unlimited stacking.

Candidate runtime sizing order:

```text
1. ABC + CAP3: safest baseline
2. ABC + CAP5: main balanced candidate
3. ABC + origin1_cap5: fallback if duplicate-origin concentration remains a concern
```

Do not approve unlimited A stacking.

## Required next step

Implement an audit-only evaluator for:

```text
fold4_rules + ABC entry gate + CAP3/CAP5 sizing
```

Then compare the same code on 2025 and 2026 before any Discord/MT5 runtime integration.
