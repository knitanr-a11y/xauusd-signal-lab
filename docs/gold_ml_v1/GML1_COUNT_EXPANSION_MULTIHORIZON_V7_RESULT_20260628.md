# GML1 Count Expansion and Multi-Horizon V7 Result

Date: 2026-06-28  
Mode: audit-only

## Objective

Use every defensible option in the existing 2023-2026 dataset before requesting older data:

1. audit where the current four sleeves lose count;
2. verify independent one-position and simultaneous-exposure effects;
3. test shorter exits on the exact current sleeves;
4. test sixteen structure-specific multi-horizon sleeves;
5. rank those sleeves with ML while retaining at least twenty percent.

No 2025 or 2026 result was used to retune a selected rule. No live runtime was changed.

## Exact current-four reconstruction

The final count audit uses the official PR63 historical builders and PR64 live execution contracts, not the earlier structural-event proxy. It reproduced the known post-2026-04-01 verification counts exactly:

- A_CORE 6;
- B_STATE 4;
- P18 2;
- W024A 2.

The current runtime uses one open parent position per sleeve. It does not apply one global position across all four sleeves.

### Independent one-position results

| Period | Trades | Positive rate | PF | R | Max DD |
|---|---:|---:|---:|---:|---:|
| 2023 | 87 | 66.67% | 2.146 | +32.07R | 5.0R |
| 2024 | 136 | 67.65% | 2.150 | +50.60R | 3.0R |
| 2025 | 245 | 64.08% | 1.834 | +72.63R | 5.0R |
| 2026 through June 19 | 64 | 67.19% | 2.123 | +23.59R | 5.0R |
| All available | 532 | 65.79% | 1.994 | +178.89R | 5.0R |

These are equal-trade R metrics for the four current sleeves. They are not the weighted six-sleeve historical headline, and P16/P19 are not included.

### Counts by sleeve

| Year | A_CORE | B_STATE | P18 | W024A | Total |
|---|---:|---:|---:|---:|---:|
| 2024 | 18 | 62 | 47 | 9 | 136 |
| 2025 | 59 | 86 | 81 | 19 | 245 |
| 2026 through June 19 | 22 | 27 | 6 | 9 | 64 |

The large variation between years is real. P18 in particular fell from 81 trades in 2025 to six in the 2026 partial period.

## Simultaneous-exposure count audit

Using actual M1 exit times after each sleeve's own one-position handling:

| Maximum simultaneous sleeves | Trades | PF | R | Rejected |
|---:|---:|---:|---:|---:|
| 1 | 494 | 1.929 | +158.89R | 38 |
| 2 | 531 | 1.988 | +177.89R | 1 |
| 3 | 532 | 1.994 | +178.89R | 0 |
| 4 | 532 | 1.994 | +178.89R | 0 |

A cap of two would historically retain all but one trade. This is an audit observation only. The current live audit runtime remains unchanged and still tracks one position independently per sleeve.

## Shorter-horizon variants of the current four

Only the holding horizon was shortened. Entry definitions, direction, target, stop, ATR and filters remained unchanged.

- A_CORE 6h to 3h: 2024 added one trade and 2025 added one trade. Both years remained above PF 1.5, but the gain was only two trades and the four-sleeve full-period R fell.
- B_STATE 48h to 24h: no extra trades in 2024 or 2025.
- P18 12h to 6h: no extra trades.
- W024A 6h to 3h: no extra trades.

Shortening the current exits is therefore not a meaningful count-expansion mechanism.

## Sixteen new multi-horizon sleeves

The existing M1 event library was grouped into sweep/reclaim, wick exhaustion, flow continuation and volatility release structures. Two pre-registered exit contracts per structure and LONG/SHORT directions created sixteen sleeves.

- raw rows: 332,432;
- exact M1 missing: zero;
- raw strict survivors: zero.

The best raw sleeve was VOL_EXTENDED-L:

- 2024: 2,104 trades, PF 0.829;
- 2025: 2,135 trades, PF 0.890.

Changing the exit contract increased count but did not create edge.

## ML ranking with a minimum twenty-percent retention

LightGBM, CatBoost and linear models were trained per sleeve on 2023. Selection used 2024. The final 2023 model and selected numeric gate were replayed unchanged in 2025 and 2026.

No 2024 sleeve passed the strict gate.

The best individual 2024 result was VOL_EXTENDED-L with a linear Strong-R score and twenty-percent retention:

- 837 trades;
- positive rate 35.01%;
- Strong PF 0.979;
- Strong R -11.41R;
- Extreme PF 0.807.

The frozen non-promotable three-sleeve fallback produced:

| Period | Trades | Strong PF | Strong R |
|---|---:|---:|---:|
| 2024 selection | 4,206 | 0.813 | -510.41R |
| 2025 unchanged | 6,519 | 0.852 | -628.52R |
| 2026 diagnostic | 3,497 | 0.896 | -230.47R |

The previous apparent high-PF subsets required extreme one- or two-percent retention. Once at least twenty percent had to remain, the ranking did not contain usable edge.

## Conclusion

The existing data-only audit is complete.

- The current four sleeves already retain independent position capacity; there was no hidden global gate suppressing hundreds of valid trades.
- Exact current-four count is higher than the earlier structural proxy suggested: 136 trades in 2024, 245 in 2025 and 64 through June 19, 2026.
- Shorter current exits add only two trades across 2024-2025.
- Sixteen new multi-horizon sleeves add thousands of trades but have PF below one.
- ML with a minimum twenty-percent retention does not rescue them.

No new sleeve or exit variant is promoted. The current four remain unchanged.

Older data is not required to repair a counting defect because no such defect remains. Older data would only be useful for discovering and validating genuinely new independent structures. The clean next evidence is prospective closed data after the current endpoint. If the project still requires a materially higher annual count after prospective accumulation, add 2021-2022 as research data rather than mixing an arbitrarily long history.

All live-ready, final-signal, Discord, MT5-order, automatic-retraining and automatic-promotion controls remain OFF.
