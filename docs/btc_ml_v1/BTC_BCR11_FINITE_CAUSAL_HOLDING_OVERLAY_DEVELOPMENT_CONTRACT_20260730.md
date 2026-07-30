# BTC BCR11 — finite causal holding-overlay development contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T20:20:00+09:00`
- status: `CONTRACT_FROZEN_IMPLEMENTATION_NEXT`
- exposure: `RETROSPECTIVE_FULL_HISTORY_EXPOSED_DEVELOPMENT`
- promotion: forbidden

## 1. Purpose

BCR10 found a broad observed split between actual exits within 16 M15 bars and actual exits at 17 bars or later. It also found that most rollover losers were already negative by 23:45, although many had a small favorable excursion earlier.

BCR11 converts that diagnosis into a small causal overlay family. It does not retune the base signal formulas and does not treat BCR10 bucket membership as a validated rule.

## 2. Frozen inputs

- BCR09 accepted package SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- BCR10 package SHA256: `99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0`
- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- execution/cost contract: BCR09 C0 and C2 exactly
- commission: zero under the frozen KIWAMI contract
- swap: not included; rollover-exposed output remains `PRE_SWAP_ONLY`

## 3. Base-machine population

Exactly six unchanged machines:

1. `TRACK_A_F1_COVERAGE_FIRST`
2. `TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE`
3. `TRACK_A_F3_STATE_FIDELITY`
4. `TRACK_A_F4_MINIMUM_EXTRA_PARETO`
5. `TRACK_B_B4_E0_EMA20_TOUCH`
6. `TRACK_B_B4_E1_EXTENSION_CONTRACT`

B1 and B2 remain outside this development family.

## 4. Exact finite overlay inventory

Each base machine is replayed under exactly six overlays:

1. `O0_BASELINE`
2. `O1_MAX_HOLD_16`
3. `O2_MAX_HOLD_32`
4. `O3_MAX_HOLD_64`
5. `O4_SERVER_DAY_FLAT_2345`
6. `O5_MAX_HOLD_16_AND_SERVER_DAY_FLAT_2345`

Total trials: `6 machines × 6 overlays = 36`.

No threshold is added after results are opened.

## 5. Max-hold semantics

- holding age is measured in theoretical 15-minute boundaries from entry;
- an entry boundary has age `0`;
- max-hold N exits at the first available decision boundary with age `>= N`;
- if the exact N boundary is missing, the first later available boundary exits and is labeled `OVERDUE_AFTER_GAP`;
- no interpolation, nearest-price or future-row substitution is used;
- the execution price is the BID-based current M15 open under the shared LONG/SHORT cost contract.

## 6. Server-day-flat semantics

- exact boundary: MT5 server open `23:45`;
- an active position exits at that boundary before any entry evaluation;
- new entries are suppressed at `23:45` for day-flat overlays;
- no same-boundary reentry occurs;
- if the exact `23:45` row is missing, no substitute boundary is used and the case is labeled `DAY_FLAT_BOUNDARY_UNAVAILABLE`.

## 7. Combined overlay semantics

`O5` exits at the first applicable event among:

- max-hold 16;
- exact 23:45 server-day flat;
- unchanged base exit.

If multiple exit reasons occur on the same boundary, execution occurs once and all coincident reason flags are retained.

## 8. State-machine order

At each available M15 decision boundary:

1. evaluate active-position overlay exits;
2. evaluate unchanged base exit;
3. execute at most one exit;
4. prohibit same-boundary reentry;
5. if still IDLE and the boundary is not entry-suppressed, evaluate unchanged base entries;
6. simultaneous LONG and SHORT base entries remain `NO_TRANSITION`.

All replays initialize `IDLE` and never read source state.

## 9. Required evaluation

For every machine/overlay/scenario and direction, report:

- entries and closed episodes;
- exit reason counts;
- holding distribution;
- C0 and C2 PF, net, expectancy and win rate;
- maximum drawdown on sequential trade PnL;
- maximum losing streak;
- month-by-month net and active month count;
- rollover-exposed episode count;
- percentage of base episodes whose exit changed;
- gap-overdue and unavailable-day-flat counts;
- deterministic two-run package SHA parity.

## 10. Multiple-trial boundary

BCR11 reports all 36 trials. It may construct a Pareto table using:

- higher C0 PF;
- higher C2 PF;
- lower absolute drawdown;
- lower rollover exposure;
- fewer changed exits as the complexity/conservatism tie-break.

It must not promote a winner, create a portfolio or call any result independent OOS evidence.

## 11. Explicit prohibitions

- no base entry or exit threshold changes;
- no TP, SL or trailing stop;
- no ATR, direction, entry-hour, weekday or regime filter;
- no alternative max-hold value;
- no other server-flat time;
- no per-machine custom overlay inventory;
- no lot optimization;
- no portfolio;
- no prospective start, shadow, Discord or MT5 order in BCR11.

## 12. Decision boundary

BCR11 is an exposed-history loss-reduction development replay. A later freeze may retain at most a small overlay proposal family, but every retained proposal requires a fresh prospective start and shadow evidence before any deployment claim.
