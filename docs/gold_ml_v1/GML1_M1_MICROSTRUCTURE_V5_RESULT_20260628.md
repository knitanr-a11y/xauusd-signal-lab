# GML1 M1 Microstructure V5 Result

Date: 2026-06-28  
Mode: audit-only  
Observed data through: 2026-06-19 19:55 MT5 server decision time

## Scope

V5 added causal M1 information available before every M5 decision:

- five-, fifteen-, thirty- and sixty-minute realized volatility;
- spread distribution and normalization;
- tick-volume burst, concentration and price alignment;
- directional efficiency, sign entropy and stagnation;
- wick imbalance and close location;
- M1 sweep/reclaim counts;
- closed M15/H1/H4/D1 context.

Every M5 decision used exact M1 entry data, no next-M1 fallback and the frozen six-hour TP1.5ATR / SL1.0ATR label. Training used 2023, selection used 2024, confirmation used unchanged 2025 configuration and 2026 was diagnostic only.

## Label-free event generation

- 245,327 M5 feature rows;
- 201,964 event proposals;
- twelve event families and twenty-four directional event candidates;
- every event candidate passed the label-free density gate;
- no event candidate passed the frozen 2024 and 2025 PF admission gates.

## Model selection in 2024

LightGBM, CatBoost and linear models were trained separately for eight microstructure direction-regime sleeves using purged 2023 out-of-fold calibration.

No sleeve passed the strict 2024 gate. A five-sleeve fallback was frozen solely to provide unchanged later-year diagnostics. It was non-promotable before 2025 and 2026 were read.

2024 fallback:

- 335 one-position trades;
- Strong positive rate 45.67%;
- Strong PF 1.129;
- Strong R +22.99;
- Extreme PF 1.002;
- Extreme R +0.33.

## Unchanged 2025 replay

- 9,359 raw rows above the frozen causal gates;
- 2,259 one-position trades;
- Strong positive rate 36.30%;
- Strong PF 0.815;
- Strong R -268.06;
- Extreme PF 0.746;
- Extreme R -381.21.

The selected score distribution did not remain calibrated. The same fixed retention configuration expanded far beyond the sparse 2024 selection.

## Unchanged 2026 diagnostic

The 2026 result covers January 2 through June 19, 2026.

- 3,642 raw rows above the frozen gates;
- 726 one-position trades;
- Base positive rate 40.36%, PF 1.007, +2.94R;
- Strong positive rate 39.26%, PF 0.954, -20.25R;
- Extreme positive rate 38.57%, PF 0.913, -38.73R.

### Monthly Strong result

| Month | Trades | Positive rate | Strong PF | Strong R |
|---|---:|---:|---:|---:|
| 2026-01 | 110 | 34.55% | 0.758 | -17.55 |
| 2026-02 | 127 | 40.94% | 1.037 | +2.80 |
| 2026-03 | 177 | 37.85% | 0.919 | -8.73 |
| 2026-04 | 96 | 46.88% | 1.318 | +15.89 |
| 2026-05 | 122 | 42.62% | 1.095 | +6.49 |
| 2026-06 through 19 | 94 | 32.98% | 0.699 | -19.16 |

### Direction

| Direction | Trades | Strong positive rate | Strong PF | Strong R |
|---|---:|---:|---:|---:|
| LONG | 416 | 38.70% | 0.922 | -19.56 |
| SHORT | 310 | 40.00% | 0.996 | -0.69 |

### Sleeve

- `MICRO_DIRECTIONAL_LONG`: 131 trades, Strong PF 1.006, +0.49R.
- `MICRO_CHAOTIC_SHORT`: 304 trades, Strong PF 0.988, -2.15R.
- `MICRO_LOW_VOL_LONG`: 281 trades, Strong PF 0.892, -18.54R.
- `MICRO_HIGH_VOL_SHORT`: six trades, Strong PF 1.485, +1.46R; insufficient support.
- `MICRO_CHAOTIC_LONG`: four trades, Strong PF 0.498, -1.51R.

## 2026 structural-event observations

Some SHORT events were positive in 2026, but none reached the frozen PF 1.5 admission level:

- `MS09-S` stagnation breakout: 199 trades, Strong PF 1.229, +24.90R, Extreme PF 1.092;
- `MS12-S` wick-imbalance reversal: 266 trades, Strong PF 1.167, +24.51R, Extreme PF 1.074;
- `MS02-S` volume-burst continuation: 475 trades, Strong PF 1.072, +19.66R, Extreme PF 1.015.

These results are diagnostic observations only. They are not eligible for promotion because the definitions were required to pass unchanged 2024 and 2025 admission first.

## Data quality

For 2026 LONG and SHORT label rows:

- total rows: 65,788;
- exact M1 missing: 240;
- unresolved Strong labels at the final data boundary or missing exact M1: 294.

## Decision

M1 spread, volume, sweep, volatility and path features materially increased candidate density, but did not create a confirmed stable edge. The strict 2024 gate had zero survivors, 2025 failed strongly and 2026 remained below PF 1 under Strong and Extreme costs.

No event or model is promoted. The current four sleeves and live runtime remain unchanged. Live-ready, final signal, Discord, MT5 orders, automatic retraining and automatic promotion remain OFF.
