# GOLD SCALP M1 MIXTURE V1 — Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_M1_MIXTURE_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`**

## Scope

The study tested whether a high-frequency GOLD portfolio could reach a median of at least 20 trades per month while allowing flexible exits under the user boundary:

- initial SL no greater than 5 USD;
- TP no lower than 5 USD;
- breakeven movement allowed;
- exact M1 resolution, fixed spread 0.30, recorded spread gate 30 points;
- protective-stop-first same-minute handling;
- one-position non-overlap.

Nine predeclared exit policies included fixed TP5/7.5/10 structures, three breakeven structures and two ATR-causal dynamic structures with TP 5–12 and SL 2–5.

## Entry engines

Thirteen causal high-frequency event engines were generated from M1/M5/M15/H1/H4/D1 data: trend resume, micro momentum, micro exhaustion fade, range reclaim, breakout hold, compression release, volume absorption, EMA snapback, spread normalization momentum, M15-boundary momentum, price-grid reaction, run continuation and run fade.

Episode onsets produced 152,712 direction-specific candidate rows.

## V1A — event exit mapping plus LightGBM quality filter

The original 18 side-policy models exceeded the execution budget before any metric. A compute-only amendment was fixed before results:

- choose one exit per event and side using TRAIN only;
- criterion: maximum TRAIN mean PnL after another 0.60 cost;
- then fit one LONG and one SHORT quality model;
- retain the same events, exits, periods, thresholds and gates.

All 22 event-side mappings had negative robust TRAIN EV after the additional cost. Selected exits were:

- TP7.5/SL3.5: 10;
- TP10/SL5: 6;
- TP5/SL2.5: 3;
- TP5/SL3: 2;
- TP10/SL5 with BE after +4: 1;
- ATR-dynamic: 0.

No absolute-score or 60-day-rank threshold passed calibration.

The strongest calibration row was causal 60-day rank P90:

- n=411;
- median monthly trades=65.5;
- WR=45.50%;
- PF=1.222;
- net=+169.39;
- PF after additional 0.60 cost=0.915;
- positive months=3/6.

Its untouched 2025+ evaluation was:

- n=2,839;
- median monthly trades=145;
- WR=30.50%;
- PF=0.862;
- net=-1,039.38;
- PF after additional 0.60 cost=0.686;
- positive half-year blocks=0/4.

The best evaluation PF anywhere in the fixed ladder was only 0.906 and remained negative.

## V1B — raw 30-M1 sequence CNN

A materially different diagnostic fed the preceding 30 exact contiguous M1 bars directly to a small CNN. Channels were return, body, range, upper/lower wick, close location, within-sequence volume z-score and spread. Static event flags and causal higher-timeframe context were concatenated. The network scored all nine exits separately for LONG and SHORT.

The original wider three-epoch CPU design exceeded the execution budget before any metric. A pre-metric compute amendment reduced width, used one epoch and larger batches while preserving sequence length, channels, events, exits, periods and gates.

No CNN threshold passed calibration.

The strongest calibration PF row was 60-day rank P90:

- n=715;
- median monthly trades=121.5;
- WR=25.59%;
- PF=0.824;
- net=-278.01.

Its 2025+ evaluation was:

- n=3,752;
- median monthly trades=144;
- WR=17.78%;
- PF=0.699;
- net=-2,672.57;
- positive half-year blocks=0/4.

## Decision

Flexible TP/SL and breakeven were not the limiting factor in these high-frequency mixtures. Frequency exceeded the target, but untouched forward quality collapsed.

Do not rescue by post-result exit, side, month, hour or volatility selection. Do not lower TP below 5 or raise SL above 5.

The next materially distinct sources would be true tick/order-flow sequences not available in the current OHLC CSVs, preregistered causal cross-market context, or a portfolio of independently frozen sparse engines accumulated under fresh prospective observation.

Frozen V19 and Challenger C1 were not read as candidate inputs and were not modified or stopped.
