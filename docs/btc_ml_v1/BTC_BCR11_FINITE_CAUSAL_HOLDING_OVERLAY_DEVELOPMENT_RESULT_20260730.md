# BTC BCR11 — finite causal holding-overlay development result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T20:39:00+09:00`
- status: `READY_RETROSPECTIVE_EXPOSED_FINITE_OVERLAY_COMPARISON_NO_PROMOTION`
- exposure: `RETROSPECTIVE_FULL_HISTORY_EXPOSED_DEVELOPMENT`
- candidate promoted: no
- portfolio selected: no
- prospective start: no
- shadow started: no

## 1. Frozen inputs and reproduction

BCR11 used only the frozen inputs and exact contract:

- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- BCR09 accepted package SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- BCR10 accepted package SHA256: `99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0`
- BCR11 contract commit: `b837d02914743bdec87d46cfbdc60683fdf511b0`

The six unchanged base machines were replayed from `IDLE` under exactly six overlays:

1. `O0_BASELINE`
2. `O1_MAX_HOLD_16`
3. `O2_MAX_HOLD_32`
4. `O3_MAX_HOLD_64`
5. `O4_SERVER_DAY_FLAT_2345`
6. `O5_MAX_HOLD_16_AND_SERVER_DAY_FLAT_2345`

Total trials: `6 × 6 = 36`.

The baseline replay reproduced every BCR09 episode for all six machines exactly, including direction, entry time, exit time and endpoint-open state. There were no missing execution rows, nearest/next fallback, interpolation, base-formula changes, TP/SL additions or per-machine custom overlays.

The result was generated twice in separate directories with identical ZIP SHA256.

- package: `BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_20260730.zip`
- accepted SHA256: `94483c7e50a50c6775c5e4140f37471e4e71c0417e5eb0ba2b6438e74bcc4339`
- deterministic repeat SHA match: true
- local tests: `4 passed`

## 2. Main result

None of the 30 non-baseline overlay trials produced positive net value or PF at least 1 under either shared scenario.

- non-baseline C0 positive trials: `0`
- non-baseline C0 PF >= 1: `0`
- non-baseline C2 positive trials: `0`
- non-baseline C2 PF >= 1: `0`

The best C0 and best C2 rows across the complete 36-trial table were both the unchanged B4 E0 baseline:

- `TRACK_B_B4_E0_EMA20_TOUCH / O0_BASELINE`
- C0 PF `1.000623`, net `+108.97 USD / 1 lot`
- C2 PF `0.949662`, net `-8,951.03 USD / 1 lot`

No overlay improves that machine into a cost-robust proposal.

## 3. Baseline versus best non-baseline overlay

| machine | baseline C0 PF / net | best non-baseline by C0 PF | non-baseline C0 PF / net | non-baseline C2 PF / net |
|---|---:|---|---:|---:|
| Track A F1 | `0.8881 / -40,703.30` | max hold 16 | `0.9103 / -39,661.41` | `0.8586 / -63,815.16` |
| Track A F2 | `0.9078 / -26,262.73` | max hold 64 | `0.9016 / -28,324.03` | `0.8535 / -42,900.28` |
| Track A F3 | `0.9319 / -12,490.33` | max hold 64 | `0.9251 / -13,720.26` | `0.8751 / -23,271.51` |
| Track A F4 | `0.9070 / -16,766.03` | max hold 64 | `0.8958 / -18,933.51` | `0.8483 / -28,046.01` |
| B4 E0 | `1.0006 / +108.97` | 23:45 flat | `0.9914 / -1,600.43` | `0.9415 / -11,110.43` |
| B4 E1 | `0.9988 / -201.97` | max hold 64 | `0.9978 / -362.97` | `0.9395 / -10,116.72` |

Only Track A F1 shows a small C0 PF/net improvement under max hold 16, but it remains materially negative and becomes more negative under C2. It is not an advancing proposal.

## 4. Why the BCR10 bucket did not transfer

BCR10 grouped trades by their **actual future base exit duration** and found that trades which happened to finish within 16 bars were strongly positive. BCR11 tested a different and causal question: what happens when the system is forcibly returned to `IDLE` at bar 16 and then continues operating normally?

The forced exit changes the later state path:

- previously blocked entry predicates may now become executable;
- new trades occur before the original base exit would have happened;
- spread is paid on those additional trades;
- later episode identity and timing diverge from baseline.

For max hold 16:

- base-episode changed share ranged from `24.25%` to `38.02%`;
- new entries caused by path divergence ranged from `108` to `553` per machine;
- all six C0 results remained negative;
- all six C2 results remained negative.

Therefore, “actual base trade ended within 16 bars” was a descriptive phenotype, not evidence that forcing every trade out at bar 16 creates value.

## 5. Server-day flat result

Exact `23:45` flat removed rollover-exposed closed episodes by construction, but did not create positive value in any machine.

Examples:

- B4 E0: C0 PF `0.9914`, net `-1,600.43`; C2 PF `0.9415`, net `-11,110.43`
- B4 E1: C0 PF `0.9802`, net `-3,399.62`; C2 PF `0.9229`, net `-13,487.12`

This confirms that rollover exposure was correlated with failure but was not itself a sufficient causal explanation or repair.

## 6. Gap and execution integrity

- max-hold exits use theoretical 15-minute age;
- one max-hold replay case exited overdue after a missing exact boundary and was explicitly labeled;
- no nearest boundary or interpolated price was used;
- exact 23:45 boundaries were not replaced by another time;
- overlay exits were processed before base exits;
- same-boundary reentry was prohibited;
- BCR09 C0 and C2 execution/cost formulas were used unchanged;
- commission remained zero under the frozen KIWAMI contract;
- swap remained excluded and rollover outputs remained `PRE_SWAP_ONLY`.

## 7. Decision

1. No BCR11 holding/day-flat overlay advances.
2. No overlay proposal family is frozen for prospective shadow.
3. No prospective start, shadow, portfolio, Discord or MT5 order is authorized.
4. Track A and the current B4 definitions remain useful audit evidence, but their current active rescue path is closed.
5. B1 remains rejected and B2 remains blocked; neither may be rescued by threshold loosening.
6. Further work should begin from a materially new, outcome-blind Track B mechanism contract rather than another timing threshold, TP/SL, trailing stop, hour filter, weekday filter or base-formula retune.

Recommended next direction, subject to explicit user authorization, is a new BCR12 independent-mechanism design stage. Candidate mechanism classes may include causal breakout/retest/re-acceleration or a separately contracted higher-timeframe regime plus lower-timeframe execution family. No new family is authorized by this result alone.