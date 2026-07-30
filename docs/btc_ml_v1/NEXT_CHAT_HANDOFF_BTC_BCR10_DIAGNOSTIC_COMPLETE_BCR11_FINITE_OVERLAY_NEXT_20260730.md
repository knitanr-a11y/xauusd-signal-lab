# NEXT CHAT HANDOFF — BTC BCR10 diagnostic complete, BCR11 finite overlay next

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T20:20:00+09:00`
- status: `BTC_REDESIGN_BCR10_DIAGNOSTIC_COMPLETE_BCR11_CONTRACT_FROZEN_IMPLEMENTATION_AWAITING_AUTHORIZATION`

## 1. Mandatory startup boundary

Read only the files listed by `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`, in order, with the branch explicitly set to `feature/btc-fresh-forward-research`.

Do not begin with `AGENTS.md`, `main`, default branch, repo-wide search, an old handoff, GOLD V3, GOLD_ML_V1, old GOLD, DISC8, Stage41, FF05 recovery V3–V11 or broad MOCHIPOYO exploration.

Collector, M7C, M8C, M9 and M10 remain running and unchanged. No BTC result is written back to GOLD/MOCHIPOYO.

## 2. Frozen evidence

- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- BCR09 accepted package SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- BCR10 accepted package SHA256: `99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0`
- BCR10 deterministic repeat SHA match: true
- BCR10 tests: `4 passed`

## 3. BCR09 state retained

Eight base machines entered the shared value gate.

- supported: `0`
- promising: `0`
- hold/cost-sensitive: `1`
- rejected: `7`
- deployable candidate: `0`
- portfolio: none
- shadow: none

B1 remains outside the current rescue path. B2 compression remains blocked and must not receive threshold rescue.

## 4. BCR10 population and integrity

Diagnostic population:

- Track A F1–F4
- Track B B4 E0/E1

Totals:

- closed episodes: `5,975`
- exact path complete: `5,829`
- explicit incomplete path: `146`
- interpolation: none
- overlay PnL: not evaluated
- candidate selection: none

Incomplete paths remain in realized holding/date/PnL summaries. MFE/MAE are left unavailable for those rows.

## 5. Main holding phenotype

Actual future-exit groups, descriptive only:

| machine | actual holding <=16 PF | net USD/1 lot | actual holding >=17 PF | net USD/1 lot |
|---|---:|---:|---:|---:|
| Track A F1 | 11.2308 | +255,519.81 | 0.1253 | -296,223.11 |
| Track A F2 | 12.7822 | +203,988.08 | 0.1393 | -230,250.81 |
| Track A F3 | 16.3127 | +137,714.88 | 0.1384 | -150,205.21 |
| Track A F4 | 15.4801 | +129,369.83 | 0.1467 | -146,135.86 |
| B4 E0 | 18.0627 | +148,974.39 | 0.1036 | -148,865.42 |
| B4 E1 | 8.5830 | +134,357.58 | 0.0801 | -134,559.55 |

Do not call this a max-hold result. Membership uses actual future exit time.

## 6. Duration versus midnight

- rollover-exposed episodes closed within 16 bars: `310`
- all six machine aggregates are positive in that group
- same-server-date episodes held 17 or more bars are negative in all six machines
- rollover-exposed episodes held 17 or more bars are also negative in all six machines

The sharper observed phenotype is continued holding, not date crossing alone.

## 7. Path diagnosis

Path-complete final losers held at least 17 bars:

- rows: `1,361`
- positive MFE at some point: `89.79%`
- first MFE median: bar `1`
- first MFE q90: bar `8`
- median MFE: `117.60 USD`
- median MAE: `1,283.80 USD`
- median giveback: `758.20 USD`

Rollover losers:

- path-complete losers: `530`
- positive at exact 23:45 before first crossing: `43`, `8.11%`
- positive MFE at an earlier point: `488`, `92.08%`
- positive-MFE losers account for `94.88%` of loss dollars
- median 23:45 PnL: `-529.80 USD`
- median final loser PnL: `-618.30 USD`

This makes max-hold the primary development anchor. Exact 23:45 flat remains a comparator but is not assumed to solve the loss path.

## 8. BCR11 frozen contract

Next stage:

`BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_REPLAY`

Exactly six overlays for each of six unchanged machines:

1. baseline
2. max hold 16 bars
3. max hold 32 bars
4. max hold 64 bars
5. exact 23:45 server-day flat
6. max hold 16 plus exact 23:45 flat

Total: `36` trials.

BCR11 uses BCR09 C0 and C2 execution/cost assumptions. It reports all trials and may create a Pareto table, but it may not promote a winner, create a portfolio or start shadow.

## 9. BCR11 causal semantics

- all machines start IDLE;
- base entry/exit formulas remain unchanged;
- overlay exit is evaluated before base exit;
- no same-boundary reentry;
- day-flat overlays suppress new entries at 23:45;
- max-hold age is measured in theoretical 15-minute boundaries;
- if the exact max-hold boundary is missing, exit at the first later available boundary and label `OVERDUE_AFTER_GAP`;
- if exact 23:45 is missing, do not substitute another time.

## 10. Current authorization boundary

BCR10 is complete. BCR11 contract is frozen, but BCR11 implementation/replay is not yet authorized in current state.

Still forbidden:

- base threshold rescue;
- TP/SL or trailing stop;
- ATR/hour/weekday/direction/regime filters;
- alternative max-hold or flat times;
- per-machine custom overlay inventories;
- lot optimization, portfolio, prospective start, shadow, Discord or MT5 order;
- modifying/stopping Collector, M7C, M8C, M9 or M10.

## 11. User action

No BAT or upload is required. The next explicit action, after authorization, is local BCR11 implementation and deterministic replay from frozen inputs.
