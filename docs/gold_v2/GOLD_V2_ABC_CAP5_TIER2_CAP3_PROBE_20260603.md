# GOLD V2 ABC CAP5 Tier2 CAP3 probe

Created: 2026-06-03
Status: audit-only / not runtime approved

## Purpose

Core is fixed:

```text
fold4_rules + ABC entry gate + CAP5 sizing
```

This probe searches only the Core REJECT rows for a Tier2 addon. Tier2 is always CAP3 sizing or lower. The goal is to increase signal count without damaging the Core.

## Selected Tier2 candidate

```text
trend_eff96 <= 0.4
AND ret96 <= -25
```

Interpretation:

```text
Low trend-efficiency pullback / sell-side continuation context.
```

## Aggregate comparison

| Dataset | View | Count | Win rate | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025 fold4 | Core ABC+CAP5 only | 200 | 65.50% | 2.38 | +230.24R | -5R | 16.20R | 5 |
| 2025 fold4 | Core + Tier2 CAP3 | 239 | 66.11% | 2.52 | +281.24R | -5R | 16.20R | 5 |
| 2026 WF | Core ABC+CAP5 only | 125 | 73.60% | 3.80 | +193.50R | -5R | 7.00R | 2 |
| 2026 WF | Core + Tier2 CAP3 | 153 | 71.24% | 3.48 | +203.50R | -5R | 7.00R | 3 |

## Tier2-only contribution

| Dataset | Tier2 count | Tier2 win rate | Tier2 PF | Tier2 TotalR | Tier2 Worst |
|---|---:|---:|---:|---:|---:|
| 2025 fold4 | 39 | 69.23% | 3.83 | +51.00R | -3R |
| 2026 WF | 28 | 60.71% | 1.77 | +10.00R | -3R |

## Monthly Core + Tier2

| Dataset | Month | Count | Win rate | PF | TotalR | Worst | MaxDD | Core count | Tier2 count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 fold4 | 2025-01 | 2 | 50.00% | 0.29 | -1.17R | -1.64R | 1.64R | 2 | 0 |
| 2025 fold4 | 2025-02 | 2 | 50.00% | 1.50 | +0.50R | -1.00R | 1.00R | 2 | 0 |
| 2025 fold4 | 2025-03 | 5 | 100.00% | inf | +17.48R | +1.64R | 0.00R | 5 | 0 |
| 2025 fold4 | 2025-04 | 35 | 71.43% | 2.79 | +32.05R | -3R | 6.00R | 23 | 12 |
| 2025 fold4 | 2025-05 | 13 | 46.15% | 1.50 | +5.00R | -3R | 3.00R | 7 | 6 |
| 2025 fold4 | 2025-06 | 4 | 25.00% | 0.40 | -3.00R | -2R | 3.00R | 4 | 0 |
| 2025 fold4 | 2025-07 | 3 | 0.00% | 0.00 | -6.78R | -3R | 6.78R | 3 | 0 |
| 2025 fold4 | 2025-08 | 3 | 33.33% | 1.09 | +0.49R | -3R | 5.51R | 3 | 0 |
| 2025 fold4 | 2025-10 | 51 | 68.63% | 3.38 | +55.29R | -3R | 8.00R | 39 | 12 |
| 2025 fold4 | 2025-11 | 62 | 72.58% | 3.07 | +107.90R | -5R | 12.03R | 56 | 6 |
| 2025 fold4 | 2025-12 | 59 | 64.41% | 2.19 | +73.48R | -5R | 16.20R | 56 | 3 |
| 2026 WF | 2026-03 | 74 | 75.68% | 5.40 | +110.00R | -3R | 3.00R | 58 | 16 |
| 2026 WF | 2026-04 | 43 | 65.12% | 2.73 | +45.00R | -5R | 5.00R | 34 | 9 |
| 2026 WF | 2026-05 | 34 | 67.65% | 2.34 | +41.50R | -5R | 7.00R | 31 | 3 |
| 2026 WF | 2026-06 | 2 | 100.00% | inf | +7.00R | +2R | 0.00R | 2 | 0 |

## Interpretation

Tier2 adds meaningful count:

```text
2025: +39 trades, +51.00R
2026: +28 trades, +10.00R
```

It does not increase worst loss beyond -5R because Tier2 remains CAP3.

However, Tier2 is not strong enough to solve every sparse month. It mainly helps 2025-04/05/10/11/12 and 2026-03/04. It barely helps 2026-05 and does not help 2025-01 to 03 or 2025-06 to 08.

## Current recommendation

```text
Core:
  fold4_rules + ABC + CAP5

Tier2 addon:
  trend_eff96 <= 0.4 AND ret96 <= -25
  sizing = CAP3
  priority = MEDIUM / audit-only
```

Do not loosen Core ABC. Keep Core quality intact and add Tier2 as a separate capped lane.

## Remaining risk

Tier2 was found by probing Core REJECT rows using 2025 and 2026 audit data. Treat it as audit-only until frozen forward validation.

Recommended next step:

```text
Build audit-only evaluator that reports:
  Core only
  Core + Tier2
  Tier2 only
  month-by-month
  signal priority HIGH/MEDIUM
```
