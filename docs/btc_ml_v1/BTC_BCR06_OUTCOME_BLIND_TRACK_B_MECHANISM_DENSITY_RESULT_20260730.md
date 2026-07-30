# BTC BCR06 — outcome-blind Track B independent-mechanism density result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:00:00+09:00`
- status: `READY_OUTCOME_BLIND_TRACK_B_DATA_CAPABILITY_RESULT`
- profitability outcomes: not opened
- trading candidates promoted: zero

## 1. Purpose

BCR06 resumes the independent Track B path. It deliberately excludes:

- RCI;
- M7C/source state;
- source-event labels;
- Track A threshold variations;
- future price or trade outcome labels.

The only questions are whether each proposed mechanism produces enough causal signals, whether the signals are spread across time, and whether they are sufficiently distinct from the four frozen Track A members.

## 2. Frozen input and causal boundary

BTC M15 source:

- path: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- server-open range: `2025-09-13 08:00:00` through `2026-07-30 06:15:00`

Contract commits:

- mechanism contract: `7b5cca370556bd41c4ef94ee4d711f11b45ac4e9`
- gap/warm-up addendum: `329c6b27ff274fbd5379beb4b80cfe6cddc6b40f`

B1, B4 and Track A overlap references required an exact contiguous 50-bar history. B2 required an exact contiguous 500-bar history. Missing bars were not interpolated or replaced with nearest observations.

## 3. Finite grammar inventory

Exactly 32 directional grammars were evaluated:

- B1 trend-pullback continuation: 8 LONG + 8 SHORT;
- B2 compression-expansion: 4 LONG + 4 SHORT;
- B4 overextension mean reversion: 4 LONG + 4 SHORT.

No grammar used current-bar high, low or close.

## 4. Track A independence reference

Each Track B signal set was compared with the actual IDLE-seeded entry-transition timestamps of all four frozen Track A complete state machines over the same M15 history.

Independence gates:

- maximum Jaccard with any Track A member: `<= 0.25`;
- maximum share of Track B fires overlapping any Track A member: `<= 0.25`.

All 32 Track B grammars passed the independence gate. Data sufficiency, rather than Track A overlap, was the limiting factor.

## 5. B1 trend-pullback continuation

All 16 B1 grammars passed the frozen data-sufficiency and independence gates.

### Advanced LONG density representative

`B1_LONG_S0_H8_C0`

Mechanism:

- bullish EMA20 > EMA30 > EMA40 stack;
- eight-bar fully closed return is negative, representing a countertrend pullback;
- immediately previous fully closed one-bar return is positive, representing resumption.

Density:

- fires: `1,943`
- distinct months: `11`
- maximum single-month share: `10.81%`
- maximum single-week share: `3.40%`
- maximum Track A overlap share: `17.14%`
- maximum Jaccard with Track A: `16.44%`

### Advanced SHORT density representative

`B1_SHORT_S0_H4_C0`

- bearish EMA stack;
- four-bar return is positive, representing a countertrend rebound;
- previous one-bar return is negative, representing bearish resumption.

Density:

- fires: `2,030`
- distinct months: `11`
- maximum month share: `10.69%`
- maximum week share: `3.20%`
- maximum Track A overlap share: `9.31%`
- maximum Jaccard: `8.43%`

These counts prove broad data availability. They do not establish edge. The signal density is high enough that a later value gate must include overlap and trade-clustering controls.

## 6. B2 compression-expansion

No B2 grammar passed the minimum data-sufficiency gate.

Observed fires among 7,611 contiguous-500 eligible rows:

### LONG

- Q20 / 20-bar breakout: `0`
- Q20 / 50-bar breakout: `0`
- Q40 / 20-bar breakout: `4`
- Q40 / 50-bar breakout: `0`

### SHORT

- Q20 / 20-bar breakout: `2`
- Q20 / 50-bar breakout: `0`
- Q40 / 20-bar breakout: `3`
- Q40 / 50-bar breakout: `0`

B2 is therefore `BLOCKED_INSUFFICIENT_CAUSAL_SIGNAL_DENSITY` under this exact current-open breakout definition. The threshold is not loosened after seeing the result. A materially different compression mechanism would be a new family and trial.

## 7. B4 overextension mean reversion

All eight B4 grammars passed data-sufficiency and independence gates.

### Advanced LONG density representative

`B4_LONG_T1p5_C0`

- previous close at least `1.5 ATR14` below EMA20;
- previous fully closed one-bar return is positive.

Density:

- fires: `828`
- distinct months: `11`
- maximum month share: `10.87%`
- maximum week share: `3.74%`
- maximum Track A overlap share: `7.97%`
- maximum Jaccard: `4.22%`

### Advanced SHORT density representative

`B4_SHORT_T1p0_C0`

- previous close at least `1.0 ATR14` above EMA20;
- previous fully closed one-bar return is negative.

Density:

- fires: `1,727`
- distinct months: `11`
- maximum month share: `11.46%`
- maximum week share: `4.81%`
- maximum Track A overlap share: `10.94%`
- maximum Jaccard: `8.22%`

B4 is substantially more independent from Track A than B1 by exact timestamp overlap.

## 8. Interpretation boundary

The four advanced grammars are data-capable entry mechanisms, not trading candidates.

The advancement rule used only:

- signal count;
- month/week dispersion;
- Track A overlap;
- finite deterministic tie-breaks.

It did not use future return, win/loss, expectancy, PF, DD, MFE or MAE.

## 9. Accepted artifact

- package: `BCR06_OUTCOME_BLIND_TRACK_B_MECHANISM_DENSITY_20260730.zip`
- SHA256: `04215689d2b861b72e737e000dfe6a6b3d2434ec2caae37b9574edd4b770027b`
- deterministic two-run SHA match: true

## 10. Decision

BCR06 passes for B1 and B4 data capability.

Frozen Track B entry proposals for the next stage:

- `B1_LONG_S0_H8_C0`
- `B1_SHORT_S0_H4_C0`
- `B4_LONG_T1p5_C0`
- `B4_SHORT_T1p0_C0`

B2 does not advance.

Before any trading-value outcome is opened, B1 and B4 require mechanism-consistent, finite exit/state-machine definitions. Track A and Track B must then enter a shared value gate under the same execution and cost contract.
