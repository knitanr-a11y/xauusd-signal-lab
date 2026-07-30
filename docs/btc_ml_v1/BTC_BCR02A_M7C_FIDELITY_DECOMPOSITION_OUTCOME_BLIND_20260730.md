# BTC BCR02A — M7C fidelity decomposition, outcome blind

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- scope: BTCUSD source fidelity only
- outcomes: not opened

## 1. Question

Why did M7C miss source alerts even though its selected trigger components appeared plausible?

Each supported BTC source event was joined to the M7C proxy decision row at the exact source `bar_time_utc`. The analysis separates:

- indicator-condition mismatch
- EMA-regime mismatch
- proxy/source state divergence
- exit threshold timing mismatch

No trade result was used.

## 2. BTC primary alerts

BTC source primary alerts:

- PRIMARY_LONG: `16`
- PRIMARY_SHORT: `9`
- total: `25`

At the exact source decision time:

- correct RCI turn direction: `25 / 25`
- correct EMA stack: `22 / 25`
- both RCI turn and EMA stack: `22 / 25`

M7C classifications:

- exact match: `14`
- missed: `11`

Among the 11 missed primary alerts:

- proxy/source state divergence: `9`
- EMA stack mismatch: `3`
- both state and EMA mismatch: `1`
- RCI turn mismatch: `0`

Therefore the primary-entry signature is not random. The RCI turn component matches every observed BTC primary source alert in this sample. Most missed primary alerts occurred because the proxy state had already diverged from source state due to an earlier unmatched transition.

## 3. BTC exits

BTC source exits:

- LONG_EXIT: `17`
- SHORT_EXIT: `9`
- total: `26`

M7C classifications:

- exact match: `13`
- one M15 bar late: `6`
- missed: `7`

At the exact source time:

- M7C exit threshold passed: `16 / 26`
- proxy state agreed with source state: `23 / 26`
- threshold and state both passed: `13 / 26`

The exit thresholds are materially less faithful than the primary RCI-turn signature. Six source exits were reproduced one bar late, showing that the threshold was often reached after the actual source exit.

## 4. Systems implication

The important failure mode is path dependence:

1. proxy misses or delays an exit;
2. proxy remains ACTIVE while source returns to IDLE;
3. a later valid source primary occurs;
4. the trigger indicators may match, but proxy rejects it because its state is still ACTIVE;
5. divergence cascades into subsequent events.

Accordingly, future Track A work must not treat every missed primary as an independent entry-condition failure.

It must separately test:

- entry trigger fidelity while source/proxy state is aligned;
- exit timing fidelity;
- explicit resynchronization policy;
- one-position state handling for a BTC candidate;
- whether source reentries/opposite events contain useful information rather than discarding them.

## 5. What is not concluded

This does not establish profitability.

It does not authorize loosening exit thresholds or adding state resynchronization based on trade outcomes. Those hypotheses must be frozen before outcome evaluation.

## 6. Next gate

Before richer trigger hypotheses are frozen, map the source event clock and prices to the exact MT5 BTC M15 candle source and confirm feature availability at decision time.
