# BTC BCR09 — shared execution, cost and retrospective value-gate contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:40:00+09:00`
- status: `CONTRACT_FROZEN_BEFORE_VALUE_OUTPUT`
- scope: `8 complete BTC M15 state machines`

## 1. Purpose

BCR09 is the first stage allowed to open trading-value outcomes for the already frozen families. It must not change a signal formula, threshold, state transition or exit after seeing PnL.

The evaluated family is exactly:

### Track A

1. `TRACK_A_F1_COVERAGE_FIRST`
2. `TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE`
3. `TRACK_A_F3_STATE_FIDELITY`
4. `TRACK_A_F4_MINIMUM_EXTRA_PARETO`

All Track A machines start `IDLE` and never read source state or source events.

### Track B

5. `TRACK_B_B1_E0_EMA30_CROSS`
6. `TRACK_B_B1_E1_STACK_BREAK`
7. `TRACK_B_B4_E0_EMA20_TOUCH`
8. `TRACK_B_B4_E1_EXTENSION_CONTRACT`

No B2 compression threshold rescue is allowed.

## 2. Frozen market input

- exact file: `btcusdsharp_m15.csv`
- frozen SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- server-open range: `2025-09-13 08:00:00` through `2026-07-30 06:15:00`

The later live file is not used.

## 3. Causal feature and state rules

- CSV `time` is MT5 broker-server bar open.
- Bars are BID-based for this exact symbol.
- A decision at bar open may use all fully closed prior M15 bars and current BID open only.
- Current high, low and close are forbidden.
- Missing M15 boundaries are not interpolated.
- Exact contiguous warm-up is required by each mechanism.
- During a feature-unavailable row an existing position state persists; no entry or exit fallback occurs.
- All machines start IDLE, hold at most one position, evaluate exit before entry, and never reenter on the same boundary.
- If exact entry or exit open is absent, the episode is invalid and the machine fails integrity; nearest/next fallback is forbidden.

## 4. Exact execution prices

Let `bid_open(t)` be CSV open and `spread_price(t) = spread(t) × 0.01`.

### LONG

- entry price: `bid_open(entry) + spread_price(entry) + entry_slippage`
- exit price: `bid_open(exit) - exit_slippage`
- profit USD per 1 lot: `exit price - entry price`

### SHORT

- entry price: `bid_open(entry) - entry_slippage`
- exit price: `bid_open(exit) + spread_price(exit) + exit_slippage`
- profit USD per 1 lot: `entry price - exit price`

Contract size is one BTC per lot. Results are reported in USD profit currency per `1.00` lot and scaled to `0.01` lot. Historical USDJPY conversion is not invented.

## 5. Cost scenarios

Commission is frozen at zero for the exact `Cryptocurrencies\\KIWAMI\\BTCUSD#` contract.

Four deterministic slippage scenarios are evaluated for every machine without selection:

- `C0_OBSERVED_SPREAD`: additional slippage `0` on both fills.
- `C1_10PCT_SPREAD_PER_FILL`: slippage is `10%` of contemporaneous spread price on each fill.
- `C2_25PCT_SPREAD_PER_FILL`: `25%` per fill.
- `C3_50PCT_SPREAD_PER_FILL`: `50%` per fill.

No candidate receives a different scenario.

## 6. Swap/rollover separation

The symbol has non-zero swap metadata, but exact historical financing charges have not been reconstructed.

Therefore BCR09 reports:

1. `NET_EX_SWAP` for all closed episodes;
2. `NO_ROLLOVER_FULL_KNOWN_COST` for episodes whose entry and exit are on the same MT5 server calendar date;
3. `ROLLOVER_EXPOSED_PRE_SWAP` separately.

No all-cost profitability claim may be made for rollover-exposed episodes. A machine cannot pass a full-known-cost gate solely on pre-swap performance from rollover-exposed trades.

## 7. Exposure labels

- Track A formulas were designed from the final source interval; all earlier application is a retrospective backcast, not OOS.
- Track A source interval is design-exposed.
- Track B formulas were selected using label-free density across the same history; the value result is outcome-blind retrospective evidence, not independent OOS.
- No result in BCR09 may be called prospective or deployable.

## 8. Required metrics

For every machine, direction, month and cost scenario:

- closed trades and endpoint-open episodes;
- wins, losses, breakeven, win rate;
- gross profit, gross loss, PF;
- net USD per 1.00 lot and 0.01 lot;
- expectancy, median trade and average win/loss;
- initial-zero maximum drawdown;
- maximum losing streak;
- active months and positive-month share;
- top-1, top-5 and top-10 profit concentration;
- LONG/SHORT contribution;
- no-rollover versus rollover-exposed counts and net;
- spread and slippage cost totals.

Monthly net-return sign evidence uses a one-sided Wilcoxon signed-rank test across active calendar months. Holm correction is applied across all eight machines separately for `C0` and `C2`. This is supporting evidence only; small monthly sample size must be shown.

## 9. Frozen classification gates

A machine is classified separately under `C0` and `C2`.

### `VALUE_SUPPORTED_RETROSPECTIVE`

All must hold:

- at least `50` closed trades total;
- at least `20` LONG and `20` SHORT closed trades;
- at least `6` active months;
- PF at least `1.20`;
- positive expectancy and positive net;
- positive-month share at least `0.60`;
- top five profitable trades contribute no more than `50%` of total positive net;
- no-rollover subset has at least `30` trades and PF at least `1.05`;
- under `C2`, PF remains at least `1.00` and net remains non-negative.

### `VALUE_PROMISING_RETROSPECTIVE`

All must hold:

- at least `50` closed trades;
- PF at least `1.10` under C0;
- positive C0 expectancy/net;
- positive-month share at least `0.50`;
- C2 PF at least `0.95`;
- no single trade supplies more than `35%` of total positive net.

### `HOLD_INSUFFICIENT_OR_COST_SENSITIVE`

Used when activity is insufficient, swap exposure prevents a full-known-cost conclusion, or C0 is positive but fixed stress destroys the edge.

### `REJECT_RETROSPECTIVE_VALUE`

Used when C0 PF is at most `1.00`, C0 net is non-positive, or the machine fails integrity.

No threshold is lowered and no new filter is added after results.

## 10. Familywise selection rule

BCR09 does not choose a portfolio.

- Report all eight machines.
- Retain every `VALUE_SUPPORTED_RETROSPECTIVE` machine.
- If none qualify, retain at most one `VALUE_PROMISING_RETROSPECTIVE` representative per mechanism family using this fixed order:
  1. higher C2 PF;
  2. higher C2 expectancy;
  3. lower C2 maximum drawdown;
  4. lower top-five concentration;
  5. lexical machine ID.
- Track A and Track B are never compared using different cost assumptions.

## 11. Integrity and prohibited actions

- no formula or threshold changes;
- no outcome-selected time, ATR, direction or regime filter;
- no TP/SL or time-stop search;
- no deleted losing trades;
- no forced close at endpoint in the primary ledger;
- no GOLD/MOCHIPOYO read or write beyond already frozen allowlisted evidence;
- no Collector/M7C/M8C/M9/M10 change;
- no Discord, MT5 order, shadow or live promotion.

## 12. Required outputs

- common reconstructed episode ledger for all eight machines;
- price/cost-enriched trade ledger;
- per-machine and per-direction metrics under C0–C3;
- monthly stability table;
- no-rollover/rollover-exposed table;
- Holm-adjusted monthly-sign evidence;
- classification and fixed tie-break manifest;
- integrity report and deterministic package hashes.

Only after BCR09 is audited may loss phenotypes, regime diagnostics and portfolio complementarity be studied. Any such study must use separate development/evaluation gates and may not rescue a rejected base machine on the same outcomes.