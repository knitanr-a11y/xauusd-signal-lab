# BTC BCR07 — outcome-blind Track B complete state-machine result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:15:00+09:00`
- status: `READY_OUTCOME_BLIND_TRACK_B_COMPLETE_STATE_MACHINE_CAPABILITY_RESULT`
- profitability outcomes: not opened
- trading candidates promoted: zero

## 1. Frozen input

- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- BCR06 package SHA256: `04215689d2b861b72e737e000dfe6a6b3d2434ec2caae37b9574edd4b770027b`
- BCR07 contract commit: `3c44e30c79d79cf4d2cc6ca6d9df8f2f583c9a20`

All machines start IDLE, hold at most one position, process exits before entries at a decision boundary, do not reenter on the same boundary, and persist state through feature-unavailable rows without fallback.

## 2. B1 trend-pullback continuation machines

### `TRACK_B_B1_E0_EMA30_CROSS`

Exit mechanism:

- LONG exits when the previous fully closed close is at or below EMA30;
- SHORT exits when the previous close is at or above EMA30.

Outcome-blind activity:

- entries: `1,980`
- closed episodes: `1,980`
- LONG / SHORT closed: `995 / 985`
- open episode at end: `0`
- median holding: `2` M15 bars
- p90 holding: `23` bars
- maximum holding: `122` bars
- position occupancy: `51.44%`
- distinct entry months: `11`
- maximum single-month entry share: `10.56%`
- maximum episode-start overlap with Track A: `14.65%`

The very short median holding is an important execution characteristic. It is not yet evidence of scalping profitability and makes cost sensitivity essential.

### `TRACK_B_B1_E1_STACK_BREAK`

Exit mechanism:

- LONG exits when the previous closed EMA alignment is no longer bullish;
- SHORT exits when it is no longer bearish.

Activity:

- entries and closed episodes: `519`
- LONG / SHORT: `249 / 270`
- open at end: `0`
- median holding: `27` bars
- p90: `103.2` bars
- maximum: `254` bars
- position occupancy: `71.34%`
- distinct months: `11`
- maximum month share: `10.60%`
- maximum Track A start overlap: `11.18%`

E0 and E1 are materially different holding-horizon mechanisms and remain separate trials.

## 3. B4 overextension mean-reversion machines

### `TRACK_B_B4_E0_EMA20_TOUCH`

Exit mechanism:

- LONG exits when the previous close reaches or exceeds EMA20;
- SHORT exits when the previous close reaches or falls below EMA20.

Activity:

- entries: `774`
- closed episodes: `773`
- LONG / SHORT closed: `304 / 469`
- open at end: `1`
- median holding: `11` bars
- p90: `31.8` bars
- maximum: `69` bars
- occupancy: `38.16%`
- distinct months: `11`
- maximum month share: `10.72%`
- maximum Track A start overlap: `17.83%`

### `TRACK_B_B4_E1_EXTENSION_CONTRACT`

Exit mechanism:

- LONG exits when negative overextension contracts to at least `-0.25 ATR14`;
- SHORT exits when positive overextension contracts to at most `+0.25 ATR14`.

Activity:

- entries: `833`
- closed episodes: `832`
- LONG / SHORT closed: `319 / 513`
- open at end: `1`
- median holding: `9` bars
- p90: `26` bars
- maximum: `65` bars
- occupancy: `33.31%`
- distinct months: `11`
- maximum month share: `10.68%`
- maximum Track A start overlap: `16.93%`

## 4. Gate result

All four machines passed the frozen capability gate:

- at least 50 closed episodes total;
- at least 20 closed episodes per direction;
- at least six entry months;
- no month above 35% of entries;
- p90 holding at most 384 bars;
- maximum holding at most 1,500 bars;
- at most one open episode at the data endpoint.

There were zero same-boundary LONG/SHORT entry conflicts in all four machines.

## 5. Interpretation boundary

BCR07 evaluates only transition density, holding duration, occupancy and timestamp overlap. The episode ledger contains no price return or win/loss field.

It does not establish:

- that the two-bar B1 E0 machine survives spread;
- that long holding in B1 E1 is profitable;
- that reaching EMA20 is an economically optimal B4 exit;
- that any Track B machine should be promoted.

## 6. Accepted artifact

- package: `BCR07_OUTCOME_BLIND_TRACK_B_STATE_MACHINES_20260730.zip`
- SHA256: `7b2643a00179aaa3b09c2854fa52e10e4bbad6ed9ff69d0a58e3d279ea7cb0f4`
- deterministic two-run SHA match: true

## 7. Decision

BCR07 passes. Four complete Track B machines are frozen for a shared Track A/Track B retrospective trading-value gate.

Before any PnL is calculated, the value gate must prove the exact MT5 symbol price-unit and cost interpretation. In particular, the CSV spread values around `2250` must not be converted into price by assumption. `digits`, `point`, `trade_tick_size`, contract size and any commission model must be captured explicitly.
