# BTC BCR15 — causal H1 impulse / M15 pullback-reclaim outcome-blind design contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-31T00:03:00+09:00`
- status: `BCR15_B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM_CONTRACT_FROZEN`
- outcome access: `B5_OUTCOME_UNOPENED`
- candidate promotion: forbidden

## 1. Authorization used

The user's instruction to keep advancing the work is treated as explicit authorization for BCR15 materially-new outcome-blind family design and the immediately following label-free implementation/capability preparation. It does not authorize value/PnL access.

## 2. Honest research position

BCR13 showed no candidate-level traction for B3: zero of eight machines passed capability. That family is closed without rescue.

The useful traction is methodological: sparse or structurally defective mechanisms are being rejected before PnL is opened. BCR15 therefore changes the economic mechanism rather than loosening B3.

## 3. New family

`B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM`

Economic statement:

A fully closed H1 directional range-expansion event creates a temporary directional auction. A trade is permitted only when a later M15 pullback enters the frozen impulse value zone without invalidating the impulse, and a subsequent fully closed M15 bar reclaims the near side of that zone with local directional displacement.

This is materially different from:

- Track A RCI/EMA source-fidelity;
- B1 generic trend pullback;
- B2 compression/expansion;
- B3 M15 structural breakout/retest/re-acceleration;
- B4 overextension mean reversion;
- BCR11 holding/rollover overlays.

## 4. Input and causal H1 construction

The frozen BTC M15 input remains:

- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- symbol: `BTCUSD#`
- BID bars
- naive MT5 broker-server timestamps
- latest row contractually closed

H1 is derived only from M15. An H1 bar is valid only when all four exact constituent M15 bars at minutes `00, 15, 30, 45` exist. Partial H1 bars, nearest rows and interpolation are forbidden.

At M15 decision boundary `t`, the newest usable H1 bar must have ended at or before `t`. The H1 bar currently forming after `t` is unavailable.

## 5. Frozen features

For a candidate fully closed H1 impulse bar `h`:

- `H1_ATR14_PRE(h)` is Wilder ATR14 through H1 bar `h-1` only.
- `PRIOR_HIGH_R(h)` is the maximum high of the exact `R` complete H1 bars immediately before `h`.
- `PRIOR_LOW_R(h)` is the minimum low of those bars.
- `IMPULSE_RANGE = high[h] - low[h]`.
- LONG origin is `open[h]`, extreme is `high[h]`.
- SHORT origin is `open[h]`, extreme is `low[h]`.
- all levels and H1 ATR are frozen for the setup and active episode.

For a closed M15 reclaim bar `m`, `M15_ATR14_PRE(m)` is Wilder ATR14 through `m-1` only.

## 6. Finite grammar

Only three dimensions vary:

- prior H1 range lookback `R ∈ {6, 12}`;
- minimum H1 impulse body `B ∈ {0.75, 1.00}` × frozen H1 ATR;
- first-pullback deadline `W ∈ {8, 16}` theoretical M15 bars after H1 impulse close.

Exactly eight machines are frozen:

1. `TRACK_B_B5_R06_B075_W08_H1_IMPULSE_M15_RECLAIM`
2. `TRACK_B_B5_R06_B075_W16_H1_IMPULSE_M15_RECLAIM`
3. `TRACK_B_B5_R06_B100_W08_H1_IMPULSE_M15_RECLAIM`
4. `TRACK_B_B5_R06_B100_W16_H1_IMPULSE_M15_RECLAIM`
5. `TRACK_B_B5_R12_B075_W08_H1_IMPULSE_M15_RECLAIM`
6. `TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM`
7. `TRACK_B_B5_R12_B100_W08_H1_IMPULSE_M15_RECLAIM`
8. `TRACK_B_B5_R12_B100_W16_H1_IMPULSE_M15_RECLAIM`

LONG and SHORT are retained symmetrically in every machine. No ninth machine, side deletion or threshold rescue is allowed.

## 7. H1 impulse predicates

LONG impulse requires all of:

1. `close[h] >= PRIOR_HIGH_R(h) + 0.25 × H1_ATR14_PRE(h)`;
2. `close[h] > open[h]`;
3. `close[h] - open[h] >= B × H1_ATR14_PRE(h)`;
4. `close[h] >= low[h] + 0.75 × IMPULSE_RANGE`.

SHORT is the exact inverse:

1. `close[h] <= PRIOR_LOW_R(h) - 0.25 × H1_ATR14_PRE(h)`;
2. `close[h] < open[h]`;
3. `open[h] - close[h] >= B × H1_ATR14_PRE(h)`;
4. `close[h] <= high[h] - 0.75 × IMPULSE_RANGE`.

An impulse arms a setup only. It does not enter.

## 8. Pullback zone and invalidation

The frozen impulse retracement zone uses the full H1 impulse range.

LONG zone:

- near boundary: `high[h] - 0.382 × IMPULSE_RANGE`;
- deep boundary: `high[h] - 0.618 × IMPULSE_RANGE`.

SHORT zone:

- near boundary: `low[h] + 0.382 × IMPULSE_RANGE`;
- deep boundary: `low[h] + 0.618 × IMPULSE_RANGE`.

The first valid pullback closed M15 bar within theoretical ages `1..W` must overlap the zone and must not invalidate the impulse.

Pre-entry invalidation:

- LONG: M15 close `< open[h] - 0.25 × H1_ATR14_PRE(h)`;
- SHORT: M15 close `> open[h] + 0.25 × H1_ATR14_PRE(h)`.

Any exact M15 gap between impulse close and entry cancels the setup.

## 9. M15 reclaim and entry

Reclaim must occur on a later closed M15 bar, never on the first pullback bar, and within four theoretical M15 bars after that pullback.

LONG reclaim requires:

1. close above the LONG near boundary;
2. bullish body;
3. body at least `0.25 × M15_ATR14_PRE(m)`;
4. close above the immediately previous exact M15 high.

SHORT is the inverse.

Entry occurs at the next exact M15 open. A missing exact entry row produces `NO_TRADE_EXACT_ENTRY_MISSING`; no later row is substituted.

## 10. Active episode exits

The active lifecycle is frozen before any outcome access.

LONG:

- success-state exit at the current exact M15 open when the previous closed M15 close is `>= impulse high + 0.50 × frozen H1 ATR`;
- structural-failure exit when the previous closed M15 close is `<= impulse open - 0.25 × frozen H1 ATR`.

SHORT is the exact inverse.

A fixed thesis-expiry exit occurs at the first exact decision boundary at or after `32` theoretical M15 bars from entry if neither structural exit occurred. This fixed expiry is part of the new event mechanism, not a post-result rescue or grid dimension.

Exit reason and holding duration may be reported in the label-free stage. Entry/exit prices, returns and win/loss labels may not.

## 11. State machine

States:

- `IDLE`
- `LONG_H1_IMPULSE_ARMED`
- `SHORT_H1_IMPULSE_ARMED`
- `LONG_PULLBACK_SEEN`
- `SHORT_PULLBACK_SEEN`
- `ACTIVE_LONG`
- `ACTIVE_SHORT`

At most one position is held. Active episodes ignore new impulses. Exits are processed before entries, and same-boundary reentry is forbidden.

Simultaneous LONG/SHORT impulse conflict is fail-closed: record the conflict and remain `IDLE`.

## 12. Gap policy

- no interpolation, nearest or next fallback;
- pending setup gap: cancel;
- missing exact next-open entry: no trade;
- active episode with missing exact previous M15 bar: decision unavailable, position persists;
- theoretical age continues across gaps for expiry reporting;
- no synthetic exit.

## 13. BCR16 label-free capability audit

The next label-free stage may implement and report all eight machines without PnL.

Frozen gate, unchanged from BCR07/BCR13:

- at least 50 closed episodes total;
- at least 20 closed LONG and 20 closed SHORT;
- at least six entry months;
- maximum single-month entry share at most 35%;
- p90 holding at most 384 M15 bars;
- maximum holding at most 1,500 M15 bars;
- at most one endpoint-open episode;
- state integrity required;
- fallback/interpolation forbidden.

All eight machines must be reported. No threshold or side rescue follows the result.

## 14. Value boundary

No return, win/loss, PF, PnL, MFE, MAE, entry price or exit price is authorized in BCR15/BCR16.

A later value stage is applicable only to BCR16 capability survivors and requires a separate explicit authorization. Historical value evidence must be described as retrospective, not independent OOS.

## 15. Decision

`FREEZE_BCR15_B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM_EIGHT_MACHINE_FAMILY_OUTCOME_UNOPENED`

No candidate is promoted. B3 remains closed. Collector, M7C, M8C, M9 and M10 remain unchanged. No GOLD/MOCHIPOYO writeback, Discord or MT5 order is permitted.
