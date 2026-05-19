# GOLD STRICT 7 SIGNAL CANDIDATES - CURRENT SCOPE

Last updated: 2026-05-19

## Purpose

This document is the current source of truth for the GOLD signal rebuild.

The previous GOLD signal candidates and previous GOLD multi-strategy candidates are no longer treated as the active design target. They remain in the repository only as historical research, implementation reference, or runtime/ledger compatibility artifacts.

The immediate goal is **not** to connect new signals to Discord, MT5 auto-trade, or AI review yet.

The immediate goal is:

```text
1. Freeze the old GOLD signal design as non-current.
2. Treat the seven strict no-future GOLD candidates below as the current main candidates.
3. Rebuild validation around these candidates only.
4. Only after validation, design a clean path into Discord notification, guarded demo autotrade, and AI review.
```

---

## Critical no-future contract

All future GOLD signal validation must obey this contract.

```text
Base trigger timeframe:
- M5 or lower only for scalping-type entries.

Minimum target size:
- At least 20 pips.
- For GOLD in the current CSV convention, 1 pip is treated as 0.10 price.
- Therefore 20 pips = 2.0 price.

Higher timeframe context:
- H1/H4/D1 may be used only when the context candle is closed.
- Required rule: context_close_time <= trigger_close_time.
- Forming H1/H4/D1 candles are not allowed in backtest validation.

Outcome:
- M1 first-touch is preferred when M1 coverage exists.
- M5 first-touch may be used only when M1 is unavailable, and this must be explicitly stated.
- Same lower-timeframe candle TP/SL conflict is counted as SL first unless a separate conservative policy is documented.

Forbidden:
- Completed H1/H4/D1 current-bar values must not be joined to a historical lower-timeframe trigger if those higher timeframe candles were not yet closed at the trigger time.
- Do not revive old signal scores based on start-time asof joins.
```

---

## Current GOLD main candidate set

The current GOLD rebuild has seven main signal candidates.

These are candidates, not yet production implementations.

### 1. SELL_KC_CCI150_LONDON_TP100_SL10

```text
Direction: SELL
Family: Keltner Channel + CCI + reversal/rejection
Session: LONDON
Target: 100 pips
Stop: 10 pips
Status: Main candidate
```

Reason for inclusion:

```text
Among the newly explored non-Donchian families, this was the cleanest SELL candidate.
It had strong PF, all-month positive behavior in the current test window, and relatively low concentration risk.
```

### 2. BUY_SWEEP_RECLAIM_RSI_TP150_SL10

```text
Direction: BUY
Family: liquidity sweep / low reclaim + RSI
Session: broad London/NY style candidate from exploration
Target: 150 pips
Stop: 10 pips
Status: Main candidate
```

Reason for inclusion:

```text
This candidate does not simply buy oversold candles.
It waits for a sweep/reclaim style recovery, which performed better than simple BB/Stoch oversold buying in weak months.
```

### 3. BUY_STOCH_BB_KTURN_NY_TP150_SL10

```text
Direction: BUY
Family: Stochastic + Bollinger Band reversal
Session: NY
Target: 150 pips
Stop: 10 pips
Additional filter: Stoch K > Stoch D
Status: Main candidate
```

Reason for inclusion:

```text
Original BUY_STOCH_BB had a weak April.
Adding Stoch K > D improved the overall result and is logically natural: buy only after stochastic starts turning upward.
```

### 4. SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5

```text
Direction: SELL
Family: H1 trend + Donchian 48 low break + MACD + range >= 1.5
Session: NY
Target: 30 pips
Stop: 7.5 pips
Status: Candidate retained
```

Reason for inclusion:

```text
This is one of the stronger Donchian-style SELL candidates.
It remains in the candidate set even though Donchian variants must be checked for monthly concentration and overlap.
```

### 5. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120

```text
Direction: SELL
Family: H1 trend + Donchian 96 low break + MACD + range >= 1.5
Session: ALL
Target: 150 pips
Stop: 37.5 pips
Cooldown: 120 minutes
Status: Candidate retained
```

Reason for inclusion:

```text
Larger-value SELL candidate.
Retained as the safer/lower-frequency Donchian96 variant.
```

### 6. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60

```text
Direction: SELL
Family: H1 trend + Donchian 96 low break + MACD + range >= 1.5
Session: ALL
Target: 150 pips
Stop: 37.5 pips
Cooldown: 60 minutes
Status: Candidate retained
```

Reason for inclusion:

```text
Same base logic as the CD120 variant, but more frequent.
It may eventually be merged with or replaced by the CD120 variant after overlap and drawdown analysis.
```

### 7. BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5

```text
Direction: BUY
Family: Bollinger Band + RSI30 + rejection candle
Session: NY
Target: 30 pips
Stop: 7.5 pips
Status: Candidate retained
```

Reason for inclusion:

```text
The first BB+RSI rejection family candidate with enough trades and acceptable PF.
It remains in the set as a shorter-target BUY candidate, separate from the larger TP150 BUY candidates.
```

---

## Explicitly non-current GOLD candidates

The following previously explored or implemented GOLD candidates are **not** the current design target.

They must not be used as the starting point for the rebuilt signal design unless the user explicitly reopens them.

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
GOLD_ALT_PF_SIGNAL_PACK_V1
GOLD_M5_SCALP_SIGNAL_PACK_V1
Existing Mochipoyo GOLD H4/M5/H4/M15/D1/H1 daytrade/scalp presets
Any GOLD candidate whose backtest depended on completed forming H1/H4/D1 values
```

Important distinction:

```text
Non-current does not necessarily mean the files must be deleted immediately.
It means they are historical and must not be treated as active research truth.
```

---

## Current implementation policy

Do not implement these seven signals directly yet.

Before implementation:

```text
1. Regenerate all seven candidates with one strict no-future research script.
2. Export full trade detail for all seven.
3. Check monthly stats.
4. Check overlap and same-time clustering.
5. Check drawdown and losing streaks.
6. Build strict backtest trade files for AI review.
7. Run AI review as hypothesis tagging only.
8. Only then design Discord/guarded demo autotrade integration.
```

---

## Required next research outputs

The next research step should produce:

```text
data/research_results/gold_strict_7_signal_candidates/
  gold_strict_7_candidates_trades.csv
  gold_strict_7_candidates_summary.csv
  gold_strict_7_candidates_monthly.csv
  gold_strict_7_candidates_overlap.csv
  gold_strict_7_candidates_portfolio_summary.json
```

The output should include all seven candidates with consistent columns:

```text
signal_id
strategy_id
candidate_family
direction
session
entry_time
entry_price
sl_price
tp_price
tp_pips
sl_pips
outcome
profit_r
profit_pips
mfe_pips
mae_pips
holding_minutes
trigger_timeframe
outcome_timeframe
strict_no_future_ok
context_h1_close_time
context_h4_close_time
context_d1_close_time
```

---

## Connection policy to Discord / autotrade / AI review

Do not connect the seven candidates to live systems until the strict research files above exist and have been reviewed.

When approved later, the connection path should be:

```text
strict signal candidate
  -> notification payload preview
  -> Discord dry-run preview
  -> guarded demo order payload preview
  -> AI review backtest ledger
  -> extended dry-run
  -> guarded demo send only after explicit approval
```

No direct MT5 send path should be added from this document alone.
