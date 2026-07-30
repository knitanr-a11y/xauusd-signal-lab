# BTC BCR04 — outcome-blind decision universe and control windows contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:12:00+09:00`
- status: `CONTRACT_FROZEN_IMPLEMENTATION_NEXT`
- scope: `BTCUSD only`
- outcome interpretation: forbidden

## 1. Why BCR04 is required

Source-alert rows alone cannot reveal a trigger signature. A condition may appear in every alert merely because it is common throughout the same market regime.

Before any Track A formula is proposed, every source event must be compared with non-event decision windows built under the same causal clock and state contract.

BCR04 is therefore not a profitability test and not a candidate search. It creates the denominator needed for later fidelity research.

## 2. Frozen inputs

### Event ledger

- BCR02 package SHA256: `5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`
- prospective start: `2026-07-20T14:54:15Z`
- BTC source-event rows after start: `76`
- BTC primary source alerts: `25`

### Candle source

- exact path: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- timestamp meaning: MT5 broker-server bar open
- inspected UTC mapping: server time = UTC + 3 hours

### M7C evidence

The accepted M7C decision package may be used only for parity and fidelity classification. It is not a trading-outcome source.

## 3. Decision-window universe

Create one row for every exact M15 decision boundary covered by the frozen source-event interval and candle snapshot.

Each row must contain:

- decision time UTC;
- current MT5 server-open;
- immediately previous fully closed M15 open time;
- propagated source state before the decision: `IDLE`, `ACTIVE_LONG`, or `ACTIVE_SHORT`;
- source transition at the exact boundary, if any;
- source event class;
- distance in M15 bars to the previous and next source event;
- detected gap flags;
- feature availability cutoff;
- outcome exposure status fixed as outcome-unseen for this stage.

No nearest, next, interpolated, or future candle fallback is permitted.

## 4. Event and control classes

Keep all classes separate:

1. `PRIMARY_LONG_EVENT`
2. `PRIMARY_SHORT_EVENT`
3. `VALID_LONG_EXIT_EVENT`
4. `VALID_SHORT_EXIT_EVENT`
5. `REENTRY_EVENT`
6. `OPPOSITE_EVENT_IGNORED`
7. `IDLE_NON_EVENT_CONTROL`
8. `ACTIVE_LONG_NON_EVENT_CONTROL`
9. `ACTIVE_SHORT_NON_EVENT_CONTROL`

No source event may be silently removed because it is difficult to reproduce.

Controls must not be selected using future price, trade result, MFE, MAE, TP, SL, or later profitability.

## 5. Control stratification

Do not rely on one hand-picked negative sample.

The full non-event universe is retained and tagged by:

- source state;
- server hour and day of week;
- local ATR or volatility band computed causally;
- distance to the nearest source event;
- RCI-turn presence and direction;
- EMA alignment;
- gap adjacency;
- recent transition age.

For focused comparisons, create deterministic strata rather than outcome-selected subsets, including:

- same-state non-event windows;
- same RCI-turn-direction non-event windows;
- same EMA-alignment non-event windows;
- near-event windows at fixed bar-distance bins;
- ordinary windows farther from all source events.

The exact distance bins and quantile boundaries must be recorded before any comparison output is inspected.

## 6. Causal M15 feature registry

BCR04 may compute a finite registry from fully closed M15 bars and current open only.

### M7C anchor features

- RCI9 level, one-bar delta, turn-up and turn-down flags;
- EMA20, EMA30, EMA40;
- EMA alignment;
- EMA20-minus-EMA30 and EMA30-minus-EMA40 in basis points.

### Additional outcome-blind context features

- RCI14 and RCI18 level and delta;
- closed-bar returns over fixed horizons;
- EMA slopes over fixed horizons;
- ATR14, ATR50 and their ratio;
- realized volatility over fixed horizons;
- Bollinger-width or equivalent compression measure;
- previous closed-bar body, range and wick ratios;
- current-open gap from previous close;
- distance to rolling high and rolling low;
- fixed rolling breakout and location flags;
- recent source-state duration and transition age;
- explicit gap and elapsed-time flags;
- broker-server hour and day of week.

Every feature must document:

- formula;
- input bars;
- earliest availability time;
- warm-up requirement;
- missing/gap behavior;
- directional interpretation, if any.

## 7. Track B capability inventory

Without opening outcomes, BCR04 also records whether the frozen M15 data can support label-free density checks for:

- trend continuation / pullback;
- volatility compression / expansion;
- breakout / re-acceleration;
- overextension / exhaustion mean reversion.

This does not select a winning Track B family. It only determines signal density, data sufficiency, and whether additional exact M5 or H1 evidence is required.

Higher-timeframe features remain forbidden until a separate exact source path and as-of close-availability contract is completed.

## 8. Required outputs

- immutable decision-window ledger;
- event/control class counts;
- source-state coverage report;
- causal feature registry;
- missingness and warm-up report;
- gap adjacency report;
- label-free feature-density report;
- Track A comparison-ready strata manifest;
- Track B data-capability inventory;
- integrity checks proving no outcome field was read.

## 9. What BCR04 must not do

- no win/loss labeling;
- no WR, PF, DD, MFE or MAE;
- no TP/SL construction or optimization;
- no threshold chosen because it improves profitability;
- no candidate promotion or rejection;
- no FF06;
- no prospective start;
- no shadow runtime;
- no modification to Collector, M7C, M8C, M9 or M10;
- no GOLD/MOCHIPOYO write-back.

## 10. Acceptance gate

BCR04 passes only if:

- every eligible M15 decision row is represented once;
- every BCR02 BTC event maps to the correct row once;
- source state propagation remains deterministic;
- control rows are created without future information;
- current high/low/close is never used;
- gaps are explicit and never filled;
- feature formulas and warm-up are reproducible;
- outputs contain no outcome-bearing field;
- all counts and hashes are recorded.

Only after BCR04 is accepted may a small Track A trigger-signature grammar and finite Track B mechanism grammar be preregistered. Formula selection and outcome evaluation remain later, separate gates.
