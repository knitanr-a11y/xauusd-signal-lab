# BTC FF05 causal candidate rebuild search contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- working branch: `feature/btc-fresh-forward-research`
- stage: `BTC_FF05_CAUSAL_CANDIDATE_REBUILD_SEARCH`
- user-facing folder: `scripts/btc_ml_v1/FF05_candidate_rebuild_search`
- search family: `BTC7N_CAUSAL_M15_TREND_IMPULSE_REBUILD_V1`

## 1. Purpose

FF03 showed that the old BTC7R implementation was directly causal but its historical high-win score was not proven to be blind validation. FF04 then passed the bar-open time contract.

FF05 evaluates the complete 108-cell family frozen before this outcome run. It does not repair BTC7R from the six FF02 losses and it does not promote any result to live use.

## 2. Mandatory time contract

The MT5 CSV `time` field is bar OPEN time.

- M15 OHLC becomes available at `M15 time + 15 minutes`.
- Entry requires the exact M5 row whose open time equals that decision time.
- Missing exact M5 entry means `NO_TRADE`.
- No nearest, next, interpolated, or future row fallback is allowed.
- H1 state is stricter than the old BTC7R implementation: only H1 rows with `H1 time + 60 minutes <= signal M15 open` are allowed.
- M5 high/low is observed at `M5 time + 5 minutes`.
- Same-M5 SL and TP contact is resolved as SL first.

Candidate logic remains in naive MT5 broker-server wall-clock time. UTC is used for the fixed cutoff and reporting.

## 3. Outcome isolation

The design cutoff is inclusive:

`2026-07-02 02:15:00 UTC`

The current broker offset recorded by FF01 converts this to the equivalent raw broker-server cutoff for the July boundary.

A bar is excluded when its availability time is after the cutoff. An exit that would require an M5 close after the cutoff is `OPEN_AT_CUTOFF` and is excluded from realized metrics.

The six FF02 losses are not used to add a filter, remove LONG, remove a time window, or change a threshold.

## 4. Fixed inherited structure clarified before the run

The following details were implicit in the old engine and are frozen before FF05 opens outcomes:

- H1 EMA50 versus EMA200 direction;
- H1 EMA200 must move in the trend direction versus the H1 state available one hour earlier;
- M15 close must be on the EMA20 trend side;
- ATR14;
- stop at the signal-bar extreme plus 0.1 ATR;
- edge-only trigger: only the first M15 bar in a consecutive qualifying run emits a signal;
- one open position per cell;
- a new entry is allowed only at or after the previous M5 exit observation time;
- $30 spread, $10 per strategy pip, 100-pip risk cap, 50-pip minimum reward;
- same-M5 SL-first;
- drawdown includes initial equity zero.

These are not selected from FF02 results.

## 5. Frozen 108-cell grid

- trend separation: `0.25 / 0.50 / 0.75 ATR`
- M15 impulse: `1.75 / 2.25 / 2.75 ATR`
- directional close location: `0.80 / 0.90`
- trend age: `0-48 / 24-96 / 48-168 hours`
- target: `1.0R / 1.5R`

Total: `108` cells. Every cell and every rejected cell must be included in the output.

## 6. Evaluation

The six frozen OOS entry segments are stitched for selection:

- OOS01: 2025-02-01 to before 2025-05-01
- OOS02: 2025-05-01 to before 2025-07-01
- OOS03: 2025-07-01 to before 2025-10-01
- OOS04: 2025-10-01 to before 2026-01-01
- OOS05: 2026-01-01 to before 2026-04-01
- OOS06: 2026-04-01 through the fixed UTC cutoff

Metrics include trades, win rate, PF, pips, total R, initial-zero max drawdown R, 2025 R, partial-2026 R, yearly concentration, trade concentration, and adjusted p-value.

## 7. Multiple-testing control

Calendar weeks are joint blocks across the complete 108-cell matrix.

- 5,000 resamples
- seed `7042901`
- one-sided studentized mean-weekly-R statistic
- null-centered max statistic across all 108 cells
- familywise adjusted p-value
- 5th percentile raw bootstrap total R as the one-sided lower bound

All cells share the same resampled week indexes on every iteration.

## 8. Survivor gates

A survivor must pass every frozen gate:

- at least 40 resolved stitched-OOS trades;
- PF at least 1.25;
- total R strictly positive;
- max DD no more than 8R;
- positive 2025 total R;
- positive partial-2026 total R;
- no single year above 70% of positive-year profit;
- no single trade above 25% of gross positive R;
- familywise adjusted p-value no more than 0.05.

Zero survivors means `NO_CANDIDATE`. Gates are not relaxed.

## 9. Selection

At most one research survivor is selected by:

1. adjusted p-value ascending;
2. bootstrap lower total R descending;
3. PF descending;
4. cell ID ascending.

A selected cell is only:

`RESEARCH_SURVIVOR_SELECTED_PENDING_RULE_FREEZE`

It is not promoted, not live-ready, and cannot begin prospective monitoring until a separate rule-freeze stage is reviewed and committed.

## 10. Safety

FF05 does not alter BTC7R, create lots, enable live use, send Discord messages, send MT5 orders, or touch GOLD/MOCHIPOYO.

Stop after uploading `99_UPLOAD_PACKAGE.zip`. No later stage is automatically authorized.
