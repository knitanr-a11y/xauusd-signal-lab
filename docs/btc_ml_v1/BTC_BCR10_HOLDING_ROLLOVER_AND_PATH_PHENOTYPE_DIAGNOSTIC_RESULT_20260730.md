# BTC BCR10 — holding, rollover and path-phenotype diagnostic result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T20:15:00+09:00`
- status: `READY_OUTCOME_EXPOSED_DIAGNOSTIC_NO_OVERLAY_SELECTION`
- candidate selected: no
- overlay PnL evaluated: no

## 1. Frozen inputs and accepted artifact

- BCR09 package SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- BCR10 package: `BCR10_HOLDING_ROLLOVER_PATH_DIAGNOSTIC_20260730.zip`
- package SHA256: `99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0`
- deterministic repeat SHA match: true
- local tests: `4 passed`

BCR10 uses the six frozen Track A/B4 machines only. B1 remains outside the rescue path.

## 2. Integrity

- closed episodes represented exactly once: `5,975`
- machines: `6`
- exact path complete: `5,829`
- explicit incomplete path cases: `146`
- interpolation or nearest/next substitution: none
- overlay exit calculation: none
- candidate, portfolio or shadow selection: none

The 146 incomplete paths remain in holding/date/PnL summaries. MFE and MAE are unavailable for those rows rather than reconstructed.

## 3. Fixed-bin counts

Holding bins:

- 1–4 bars: `1,227`
- 5–8: `1,284`
- 9–16: `1,530`
- 17–32: `1,232`
- 33–64: `572`
- 65–128: `129`
- 129 or more: `1`

Server-date crossings:

- D0: `5,018`
- D1: `950`
- D2: `7`

## 4. Main phenotype: 16 bars versus 17 or more

The actual-exit holding buckets show a common split across all six machines.

| machine | observed holding <=16 PF | net USD/1 lot | observed holding >=17 PF | net USD/1 lot |
|---|---:|---:|---:|---:|
| Track A F1 | 11.2308 | +255,519.81 | 0.1253 | -296,223.11 |
| Track A F2 | 12.7822 | +203,988.08 | 0.1393 | -230,250.81 |
| Track A F3 | 16.3127 | +137,714.88 | 0.1384 | -150,205.21 |
| Track A F4 | 15.4801 | +129,369.83 | 0.1467 | -146,135.86 |
| B4 E0 | 18.0627 | +148,974.39 | 0.1036 | -148,865.42 |
| B4 E1 | 8.5830 | +134,357.58 | 0.0801 | -134,559.55 |

These are descriptive groups formed from the actual future exit time. They are not the result of forcing an exit at bar 16 and do not validate a max-hold overlay.

The direction-level result is also broad: every LONG and SHORT cell is positive for 1–8 bars; 11 of 12 are positive for 9–16 bars. Every one of the 12 machine-direction cells is negative at 17 bars or more.

## 5. Duration is more direct than date crossing

The BCR09 same-server-date split was not solely a midnight effect.

- rollover-exposed episodes closed within 16 bars: `310`
- each of the six machine aggregates is positive in that group
- same-server-date episodes held 17 bars or more are negative in every machine
- rollover-exposed episodes held 17 bars or more are also negative in every machine

Therefore server-date crossing is strongly correlated with failure, but the sharper observed separator is continued holding beyond 16 M15 bars. This remains outcome-exposed diagnosis, not a causal rule.

## 6. Path of long-held losers

Population: path-complete trades held at least 17 bars that ended as C0 losses.

- rows: `1,361`
- fraction with positive MFE at some point: `89.79%`
- first MFE bar median: `1`
- first MFE bar 90th percentile: `8`
- median MFE: `117.60 USD` per 1 lot
- median MAE: `1,283.80 USD`
- median peak-to-exit giveback: `758.20 USD`

The common pattern is an early small favorable excursion followed by a much larger adverse move while the original state machine continues holding.

## 7. Rollover-loser diagnosis

- rollover-exposed episodes: `957`
- final C0 losers: `582`
- path-complete losers: `530`
- positive at exact 23:45 before first crossing: `43 / 530 = 8.11%`
- positive MFE at any earlier point: `488 / 530 = 92.08%`
- share of rollover-loser loss dollars from positive-MFE losers: `94.88%`
- median 23:45 PnL: `-529.80 USD`
- median final loser PnL: `-618.30 USD`
- median giveback among positive-MFE rollover losers: `948.90 USD`

An exact 23:45 flat could still reduce later losses, but most rollover losers are already negative by 23:45. It is therefore not the strongest first explanation. The observed path points more directly to maximum-holding control.

## 8. Formula boundary

- LONG path starts at spread-adjusted entry ask and uses BID highs/lows while open.
- SHORT path starts at entry BID and uses contemporaneous spread-adjusted ask lows/highs.
- exit-bar high and low are excluded because the position exits at that bar's open.
- the actual exit open is included.
- entry ATR14 is from the immediately previous fully closed M15 bar.
- no missing path is interpolated.

## 9. Decision

BCR10 passes as an exposed-history diagnostic.

It establishes a clear development hypothesis:

1. retain the unchanged base machines;
2. test a finite causal maximum-holding family at 16, 32 and 64 bars;
3. keep exact 23:45 server-day flat as a separate comparator;
4. include one preregistered combination using 16 bars and 23:45;
5. do not add TP/SL, ATR, weekday, entry-hour, direction or discretionary filters.

No overlay has been evaluated or promoted in BCR10. Any BCR11 improvement remains retrospectively exposed and requires a new prospective shadow family before deployment claims.
