# NEXT CHAT HANDOFF — BTC AI V1 Stage55 active / simple-rule anti-overfit preregistration next

Date: 2026-08-04

## Repository and current branch

- repo: `knitanr-a11y/xauusd-signal-lab`
- current authoritative archive/runtime branch: `feature/btc-ai-v1-data-acquisition`
- PR: `#99`
- PR state: open / Draft / unmerged

## Mandatory read order

Read the following from the branch above, in this exact order, from beginning to end.

1. `START_HERE_BTC_AI_V1.md`
2. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX_V2_20260804.md`
3. `docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_RESEARCH_RECORD_THROUGH_STAGE55_AND_SIMPLE_RULE_NEXT_20260804.md`
4. `docs/btc_ai_v1/BTC_AI_V1_SIMPLE_RULE_ANTI_OVERFIT_RESEARCH_DESIGN_20260804.md`
5. `config/btc_ai_v1/simple_rule_anti_overfit_research_contract_20260804.json`
6. `config/btc_ai_v1/current_state_stage55_20260804.json`
7. `config/btc_ai_v1/next_action_simple_discretionary_rules_20260804.json`
8. `docs/btc_ai_v1/BTC_AI_V1_STAGE55_DUAL_REVERSE_SHORT_PROSPECTIVE_SHADOW_20260804.md`
9. `config/btc_ai_v1/stage55_dual_reverse_short_shadow_contract_20260804.json`

Do not begin implementation or historical outcome calculation until all nine have been read.

## Current formal status

`BTC_AI_V1_STAGE55_ACTIVE_OBSERVATION_CONTINUES_SIMPLE_RULE_ANTI_OVERFIT_PREREGISTRATION_NEXT`

## Stage55 — already active and frozen

User-PC activation succeeded.

- status: `READY_NO_BACKFILL_ACTIVATED`
- cutoff: `2026-08-04 10:52:00` MT5 broker-server time
- accepted candidates at activation: 0
- runtime state root: `%LOCALAPPDATA%/xauusd_signal_lab/btc_stage55_shadow`
- Shadow observation loop: user reported started
- Discord entry sidecar: user reported started
- explicit receipt of the real Discord test message is not claimed unless the user later confirms it

Frozen families:

1. `M1_CP30_Q70_M1_BEARISH_EMA20_15M_SHORT_TP2R_MAX240`
2. `M5_LEVEL_REJECTION_010_M5_TWO_BAR_BEARISH_SHORT_TP2R_MAX480`

Do not change:

- model
- Q70
- confirmation timing
- stop
- target
- maximum hold
- family membership
- activation cutoff
- no-backfill state
- Discord delivery scope

Do not delete or recreate the Stage55 state directory. Do not mix new research code into the Stage55 checkout.

## Why a new research cycle is allowed

Stage55 is too low-frequency to be the only continuing BTC research path. The user explicitly wants additional research and suspects that simple discretionary-style rules may be more robust than complex AI or large parameter searches.

The new cycle is authorized, but must be completely separate from Stage55.

Proposed new branch:

`feature/btc-simple-discretionary-rule-research`

Proposed separate clone:

`C:\xauusd-signal-lab-btc-simple-rules`

The new branch has not yet been created unless GitHub shows otherwise. Confirm before creating it. Do not switch the running Stage55 checkout to another branch.

## Historical-data interpretation

2023 through 2026-07 OHLC has been heavily consumed by prior research. Therefore, new historical results over this period are not a true untouched holdout.

This does not prohibit research. It means:

- historical results are retrospective exploratory evidence;
- rules must be frozen before outcomes are opened;
- the search space must remain small;
- final promotion requires fresh no-backfill prospective evidence.

Do not claim that a historical slice is truly unused merely because the new script did not train on it. Human knowledge from previous research is also a source of selection bias.

## Next task — preregistration only

The immediate next task is not to run a backtest.

First, prepare a user-reviewable preregistration for at most four simple deterministic families:

1. `HTF_TREND_PULLBACK_RECLAIM_RESUME`
2. `PREVIOUS_OR_LOOKBACK_HIGH_LOW_SWEEP_CLOSE_BACK`
3. `COMPRESSION_BREAKOUT_FIRST_RETEST`
4. `ATR_IMPULSE_EXHAUSTION_SIMPLE_REVERSAL`

For each family, propose exactly:

- direction policy
- timeframes
- at most one higher-timeframe context
- one setup
- one confirmation
- decision timestamp
- exact M1 entry timestamp
- fixed stop
- fixed target
- fixed maximum hold
- same-M1 collision rule
- missing-M1 rule
- one-position/non-overlap rule
- frequency floor
- numerical acceptance/rejection gates
- at most two robustness neighbors

The user must approve or correct these before any PnL/PF/win-rate result is calculated.

## Anti-overfit limits

- maximum families: 4
- base rules per family: 1
- maximum robustness neighbors per family: 2
- maximum configurations total: 12
- first pass: deterministic only, no ML
- neighbors are stress tests, not selectable replacement candidates
- if base fails and neighbor passes, do not promote the neighbor
- do not select the maximum-PF configuration
- do not add a fifth family after seeing results
- do not retain only a profitable direction, month, session, D1 state, ATR state or year
- do not relax thresholds to rescue frequency after results
- do not delete negative results

## Fixed data and execution authority

- symbol: XM `BTCUSD#`
- closed OHLC only: M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- exact M1 entry only
- missing exact entry M1: invalidate, no fallback
- same-M1 TP/SL collision: SL first
- roundtrip cost: 22.50 USD per completed 1 BTC trade
- no external markets, funding, open interest, order flow, tick volume or real volume

## Temporal reporting after freeze

Only after full rule and gate freeze, execute one formal historical run and report all families together.

- 2023: implementation/event sanity audit
- 2024: temporal stress slice A
- 2025: temporal stress slice B
- 2026-01 through 2026-07: consumed diagnostic slice C

Do not modify rules between slices.

## Required metrics after authorization to run

- trades and trades/month
- win rate
- PF
- net
- maximum drawdown
- year/half-year/month results
- direction split when applicable
- maximum winner removed
- double-cost result
- base versus preregistered neighbors
- profit concentration by month and top trades
- exact-M1 gap count
- overlap and same-M1 collision audit

## Promotion boundary

Even if historical results pass, the maximum status is:

`RESEARCH_CANDIDATE_REQUIRES_FRESH_PROSPECTIVE_CONFIRMATION`

A separately activated no-backfill Shadow is required before any promotion.

Still OFF:

- MT5 orders
- live trading
- live-ready
- final signal
- automatic promotion

## Operating style

The user has explicitly requested:

- do not guess;
- ask when something is genuinely ambiguous;
- do not silently change contracts;
- preserve all negative results;
- explain changes and reasons in Japanese;
- do not claim GitHub changes unless they were actually committed.

## First response in the next chat

After reading the mandatory files, report:

1. the confirmed branch/head and PR state;
2. Stage55 frozen active status and cutoff;
3. confirmation that the new simple-rule cycle is separate;
4. the proposed preregistration for the four families;
5. any genuine ambiguities requiring user decision.

Do not run research yet.
