# BTC BCR12 — materially new outcome-blind Track B mechanism design contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T21:57:00+09:00`
- status: `BCR12_B3_BREAKOUT_RETEST_REACCELERATION_CONTRACT_FROZEN`
- stage: `BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN`
- outcome access: `B3_OUTCOME_UNOPENED`
- implementation: not started
- candidate promotion: forbidden

## 1. Authorization and boundary

The user explicitly authorized continuation after the BCR11 handoff review. This authorization permits BCR12 mechanism-contract creation only in this work step.

It does not authorize:

- opening B3 return, win/loss, PF, MFE, MAE or future-exit outcomes;
- BCR13 implementation or density execution;
- BCR14 retrospective value evaluation;
- prospective start, shadow, Discord, MT5 order or live-ready status;
- rescue or retuning of Track A, B1, B2 or B4.

## 2. Materially new economic mechanism

BCR12 freezes a new Track B family:

`B3_BREAKOUT_RETEST_REACCELERATION`

Economic statement:

A directional structural break may create value only when price first closes beyond a prior range, subsequently revisits the broken level without closing through the invalidation zone, and then produces a second closed-bar directional displacement. The entry is taken only after that re-acceleration bar is fully closed.

This differs materially from:

- Track A RCI/EMA source-fidelity machines;
- B1 trend-pullback continuation machines;
- B2 compression/expansion density work;
- B4 overextension mean reversion;
- BCR11 holding-time and server-day-flat overlays.

No BCR09-BCR11 losing subset, hour, weekday, direction, ATR regime or future holding result is used to choose a B3 signal.

## 3. Frozen market input

- frozen BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- symbol: `BTCUSD#`
- bar side: BID
- clock: naive MT5 broker-server M15 open timestamps
- latest CSV row contract: closed
- no higher-timeframe input in BCR12

B3 historical evaluation, if later authorized, is retrospective and not independent OOS evidence because other BTC family outcomes have already been viewed. B3 formulas themselves are frozen before any B3 outcome is opened.

## 4. Causal availability contract

At decision boundary `t`, the machine may use only:

- the exact M15 bar with open `t-15m`, after that bar is fully closed;
- earlier fully closed exact M15 bars;
- deterministic values computed from those bars;
- the current exact M15 open at `t` only as an execution observation after a signal has already been fixed from closed history.

It may not use:

- high, low or close of the bar opening at `t`;
- any future bar or future exit information;
- nearest, next, interpolated or synthetic rows;
- source labels, M7C state or GOLD/MOCHIPOYO outcomes;
- H1/H4/D1 information;
- BCR09-BCR11 outcome-derived filters.

## 5. Deterministic feature definitions

For a fully closed candidate breakout bar `j`:

- `ATR14_PREBREAK(j)` is Wilder ATR14 through bar `j-1` only.
- `UPPER_L(j)` is the maximum high of the exact `L` fully closed bars immediately preceding `j`, excluding `j`.
- `LOWER_L(j)` is the minimum low of the same preceding `L` bars.
- all required bars must be exactly contiguous at 15-minute spacing;
- if the lookback or ATR input is unavailable, no breakout is emitted.

Fixed constants, common to every machine:

- breakout body floor: `0.25 × ATR14_PREBREAK`;
- retest-zone half width: `0.25 × ATR14_PREBREAK`;
- pre-entry invalidation distance: `0.50 × ATR14_PREBREAK`;
- re-acceleration displacement: `0.25 × ATR14_PREBREAK`;
- re-acceleration body floor: `0.25 × ATR14_PREBREAK`;
- re-acceleration deadline after first retest: `4` theoretical M15 bars;
- active structural-failure exit distance: `0.50 × ATR14_PREBREAK`.

ATR, breakout level and all distances are frozen from the breakout event and are not recomputed for that pending or active episode.

## 6. Exact finite grammar

Only these dimensions vary:

- structural lookback `L ∈ {32, 64}`;
- breakout displacement `D ∈ {0.25, 0.50}` ATR;
- first-retest deadline `W ∈ {4, 8}` theoretical M15 bars after the breakout bar.

Exactly eight machines are frozen:

1. `TRACK_B_B3_L32_D025_W04_BREAK_RETEST_REACCEL`
2. `TRACK_B_B3_L32_D025_W08_BREAK_RETEST_REACCEL`
3. `TRACK_B_B3_L32_D050_W04_BREAK_RETEST_REACCEL`
4. `TRACK_B_B3_L32_D050_W08_BREAK_RETEST_REACCEL`
5. `TRACK_B_B3_L64_D025_W04_BREAK_RETEST_REACCEL`
6. `TRACK_B_B3_L64_D025_W08_BREAK_RETEST_REACCEL`
7. `TRACK_B_B3_L64_D050_W04_BREAK_RETEST_REACCEL`
8. `TRACK_B_B3_L64_D050_W08_BREAK_RETEST_REACCEL`

Each machine evaluates LONG and SHORT symmetrically. A later result may not delete a direction, add direction-specific thresholds or create a ninth machine inside this family.

## 7. Breakout predicates

LONG breakout on closed bar `j` requires all of:

1. `close[j] >= UPPER_L(j) + D × ATR14_PREBREAK(j)`;
2. `close[j] > open[j]`;
3. `close[j] - open[j] >= 0.25 × ATR14_PREBREAK(j)`.

SHORT breakout is the exact inverse:

1. `close[j] <= LOWER_L(j) - D × ATR14_PREBREAK(j)`;
2. `close[j] < open[j]`;
3. `open[j] - close[j] >= 0.25 × ATR14_PREBREAK(j)`.

A valid breakout moves the machine from `IDLE` to the corresponding `BREAKOUT_ARMED` state at the next exact decision boundary. It does not enter a position.

## 8. Retest predicates

For an armed LONG breakout with frozen level `U` and ATR `A`, the first valid retest closed bar `k` must occur within theoretical ages `1..W` and satisfy:

- `low[k] <= U + 0.25A`;
- `close[k] >= U - 0.25A`.

For an armed SHORT breakout with frozen level `L0`:

- `high[k] >= L0 - 0.25A`;
- `close[k] <= L0 + 0.25A`.

Before a retest is accepted, the pending setup is cancelled if:

- LONG: a closed bar has `close < U - 0.50A`;
- SHORT: a closed bar has `close > L0 + 0.50A`;
- no valid retest occurs by age `W`;
- any exact M15 boundary is missing between breakout and retest.

The first valid retest only is retained. Retest-bar high/low and time are frozen.

## 9. Re-acceleration and entry

Re-acceleration must occur on a later closed bar, never on the retest bar itself, and no later than four theoretical M15 bars after the retest.

LONG re-acceleration requires all of:

1. `close[m] >= U + 0.25A`;
2. `close[m] > open[m]`;
3. `close[m] - open[m] >= 0.25A`;
4. `close[m] > max(high[k..m-1])`.

SHORT re-acceleration requires all of:

1. `close[m] <= L0 - 0.25A`;
2. `close[m] < open[m]`;
3. `open[m] - close[m] >= 0.25A`;
4. `close[m] < min(low[k..m-1])`.

A valid re-acceleration emits an entry for the next exact M15 open. If that exact entry row is absent, the setup becomes `NO_TRADE_EXACT_ENTRY_MISSING`; no later or nearest entry is used.

If invalidation occurs or the four-bar re-acceleration deadline expires first, the setup returns to `IDLE` without entry.

## 10. Active-position exit

The B3 exit is structural thesis failure, not a BCR11 rescue overlay.

- LONG exits at the current exact M15 open when the immediately previous exact closed bar has `close < frozen_breakout_level - 0.50 × frozen_ATR`.
- SHORT exits at the current exact M15 open when the previous exact closed bar has `close > frozen_breakout_level + 0.50 × frozen_ATR`.

There is:

- no TP;
- no intrabar SL;
- no trailing stop;
- no maximum-hold exit;
- no server-day flat;
- no hour, weekday, ATR-regime or direction filter.

An active position ignores new breakout setups. Endpoint-open positions remain explicitly open and are not force-closed.

## 11. State-machine order

States:

- `IDLE`
- `LONG_BREAKOUT_ARMED`
- `SHORT_BREAKOUT_ARMED`
- `LONG_RETEST_SEEN`
- `SHORT_RETEST_SEEN`
- `ACTIVE_LONG`
- `ACTIVE_SHORT`

At each exact decision boundary:

1. validate that the immediately previous exact M15 bar exists and is closed;
2. process an active-position structural-failure exit;
3. prohibit same-boundary reentry after an exit;
4. process pending invalidation, gap cancellation and expiry;
5. process retest or re-acceleration transitions;
6. execute at most one scheduled entry at the exact current open;
7. if still `IDLE`, evaluate new breakout predicates from the previous closed bar.

All machines initialize `IDLE`, hold at most one position and never read source state.

## 12. Gap behavior

- no interpolation, nearest or next fallback;
- a gap anywhere between breakout and entry cancels that pending setup as `CANCEL_GAP_IN_SEQUENCE`;
- theoretical age continues across clock gaps for expiry reporting;
- while active, a decision is unavailable if the exact previous M15 bar is missing; the position persists and the boundary is labeled `ACTIVE_DECISION_UNAVAILABLE_GAP`;
- no synthetic exit is invented;
- gap counts and affected episodes must be reported separately.

## 13. BCR13 outcome-blind capability gate

The next recommended stage is:

`BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`

BCR13 may calculate only label-free capability information:

- breakout, retest, re-acceleration, entry, exit and cancellation counts;
- LONG/SHORT counts;
- monthly event density and maximum month concentration;
- holding-bar distribution and position occupancy;
- pending-state age distribution;
- exact-entry-missing, gap-cancel and active-gap counts;
- simultaneous-conflict counts;
- overlap timestamps with frozen Track A/B1/B4 ledgers, without reading their PnL;
- deterministic repeat SHA.

A machine passes capability only if all are true:

- at least `50` closed episodes total;
- at least `20` closed episodes in each direction;
- at least `6` entry months;
- no month exceeds `35%` of entries;
- p90 holding is at most `384` M15 bars;
- maximum holding is at most `1500` M15 bars;
- at most one endpoint-open episode;
- state and one-position integrity tests pass;
- no fallback or interpolated row is used.

These are the existing BCR07 capability thresholds reused unchanged. They were not selected from B3 outcomes.

All eight machines must be reported. A failed machine may not be rescued by threshold loosening, side deletion or a larger grid.

## 14. Later value-gate boundary

No B3 PnL is authorized in BCR12 or BCR13.

A later separately authorized value stage must:

- evaluate only BCR13 capability survivors;
- use the frozen BCR09 symbol/execution/cost contract, including C0 and C2;
- separate raw, deduplicated and complete-state-machine results where applicable;
- report direction, month, volatility and trend-regime breakdowns without using them as post-result filters;
- apply trial-count and multiple-testing control across every opened B3 machine;
- describe all historical B3 results as retrospective, not independent OOS;
- require a newly committed prospective boundary before shadow claims.

## 15. Explicit prohibitions

- no Track A/B1/B2/B4 retune or rescue;
- no BCR11 max-hold or flat-time continuation;
- no additional lookback, displacement, retest-window or buffer value;
- no outcome-based machine deletion;
- no LONG-only or SHORT-only rescue;
- no higher-timeframe, volume, funding, order-book or external context in this family;
- no portfolio construction;
- no prospective start or shadow;
- no Discord, MT5 order, live-ready or final signal;
- no Collector, M7C, M8C, M9 or M10 modification;
- no GOLD/MOCHIPOYO writeback.

## 16. Decision

BCR12 freezes one materially new B3 mechanism and eight exact outcome-unopened machines.

Current decision:

`FREEZE_BCR12_B3_BREAKOUT_RETEST_REACCELERATION_FAMILY_AWAIT_EXPLICIT_BCR13_AUTHORIZATION`

No candidate is promoted. No outcome is opened. No implementation or BAT is created in BCR12.