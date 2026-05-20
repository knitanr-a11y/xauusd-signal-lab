# GOLD Strict 7 Backtest AI Review - Initial Result

Last updated: 2026-05-19

## Purpose

This document freezes the first completed AI review result for the current GOLD strict seven-signal candidate set.

This is a **backtest AI review** report, not a live-performance report.

The AI review result is used for hypothesis tagging only.

It must not be used to:

```text
- stop a signal automatically
- block orders automatically
- change lot size automatically
- rewrite strategy rules from one trade or one tag
- mix backtest results with live results
```

---

## Source files

Primary output directory:

```text
data/runtime_logs/trade_ai_review_backtest_gold_strict_7/
```

Important files:

```text
trade_outcome_ledger.csv
trade_feature_snapshot.csv
trade_feature_snapshot.jsonl
trade_ai_review_payloads.jsonl
trade_ai_review_ledger.jsonl
trade_ai_review_run_summary.json
trade_ai_review_resume_run_summary.json
trade_ai_tag_summary.csv
trade_ai_tag_summary.json
gold_strict_7_ai_review_resume_summary.json
```

Related strict signal output directory:

```text
data/research_results/gold_strict_7_signal_candidates/
```

---

## Completion status

The AI review completed successfully after resuming the partial run.

```text
payload_rows: 314
review_rows: 314
remaining_payload_rows_after_resume: 0
run_mode: OPENAI_API
model: gpt-5-mini
error_rows on resumed 196-row run: 0
```

The completed tag summary reports:

```text
reviews_in: 314
tag_rows: 1846
summary_rows: 118
should_investigate_rows: 23
```

The earlier failure was caused by API quota exhaustion, not by prompt/schema/parser logic.
After quota became available again, the remaining 196 reviews completed successfully.

---

## Review sample design

The AI review was run on a balanced, loss-weighted sample, not the full strict backtest trade set.

Default sampling policy:

```text
- include all wins
- include losses up to 2x wins per strategy
- keep backtest AI review separate from live AI review
```

Sample size:

```text
source evaluated rows: 520
selected rows: 314
selected wins: 111
selected losses: 203
```

Per-strategy AI review sample counts:

| strategy_id | reviewed rows | wins | losses |
|---|---:|---:|---:|
| BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5 | 48 | 20 | 28 |
| BUY_STOCH_BB_KTURN_NY_TP150_SL10 | 78 | 26 | 52 |
| BUY_SWEEP_RECLAIM_RSI_TP150_SL10 | 57 | 19 | 38 |
| SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5 | 23 | 10 | 13 |
| SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120 | 39 | 13 | 26 |
| SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60 | 42 | 14 | 28 |
| SELL_KC_CCI150_LONDON_TP100_SL10 | 27 | 9 | 18 |

Important:

```text
These sample-level win rates / PF values are not the same thing as the full backtest result.
They are used to compare AI tags inside the reviewed sample.
```

---

## Sample-level performance snapshot

The reviewed 314 rows produced the following sample-level stats:

| strategy_id | reviewed rows | win rate | total R | PF | max losing streak |
|---|---:|---:|---:|---:|---:|
| BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5 | 48 | 41.67% | +38.92R | 2.09 | 7 |
| BUY_STOCH_BB_KTURN_NY_TP150_SL10 | 78 | 33.33% | +321.50R | 6.08 | 11 |
| BUY_SWEEP_RECLAIM_RSI_TP150_SL10 | 57 | 33.33% | +234.51R | 6.01 | 12 |
| SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5 | 23 | 43.48% | +20.51R | 2.24 | 4 |
| SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120 | 39 | 33.33% | +21.30R | 1.77 | 6 |
| SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60 | 42 | 33.33% | +23.13R | 1.78 | 6 |
| SELL_KC_CCI150_LONDON_TP100_SL10 | 27 | 33.33% | +66.77R | 4.10 | 6 |

Interpretation:

```text
- The AI review sample is intentionally loss-heavy.
- Even under loss-heavy sampling, several large-TP strategies remain strongly positive.
- The Donchian96 variants remain the weakest sample-level group.
```

---

## Main AI tag findings

### 1. BUY_STOCH_BB_KTURN_NY_TP150_SL10

This strategy remains attractive because the large TP can dominate total R.
However, AI tags confirm that the drawdown/losing-streak risk is concentrated in poor reversal structure.

Important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| poor_pullback_structure | 42 | 5 | 37 | +0.69R | 1.64 | weak compared with strategy sample avg |
| macd_late_signal | 9 | 1 | 8 | +0.58R | 1.55 | small sample but clearly weak |
| near_recent_high | 16 | 3 | 13 | +1.80R | 2.84 | weaker than baseline |
| entry_after_extended_move | 65 | 21 | 44 | +3.96R | 5.81 | common tag; not enough alone to block |

Interpretation:

```text
BUY_STOCH_BB should not be removed.
The more useful monitoring tag is poor_pullback_structure, not just entry_after_extended_move.
```

Practical monitoring rule later:

```text
Do not auto-block yet.
Track whether live BUY_STOCH_BB losses repeatedly receive poor_pullback_structure and/or macd_late_signal.
```

---

### 2. BUY_SWEEP_RECLAIM_RSI_TP150_SL10

The AI review suggests this candidate is highly dependent on reclaim quality.
Weak reclaim / poor pullback structure is the main risk cluster.

Important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| poor_pullback_structure | 29 | 4 | 25 | +0.99R | 1.94 | weak compared with strategy sample avg |
| m15_signal_candle_large | 26 | 4 | 22 | +1.24R | 2.18 | often appears in weaker cases |
| high_volatility_chase | 16 | 3 | 13 | +1.77R | 2.76 | watch as chase-risk tag |
| near_recent_high | 6 | 1 | 5 | +1.49R | 2.51 | small sample, weak |

Interpretation:

```text
The strategy can still win because TP is large, but weak reclaim quality makes losses frequent.
Do not disable it, but compare live losers with poor_pullback_structure and high_volatility_chase.
```

---

### 3. BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5

This shorter-target BUY is more sensitive to immediate bad entry quality.
The strongest negative tags are high volatility and large signal candle.

Important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| high_volatility_chase | 10 | 1 | 9 | -0.78R | 0.32 | strongest bad tag in this sample |
| m15_signal_candle_large | 25 | 4 | 21 | -0.47R | 0.56 | clear caution tag |
| range_edge_entry | 19 | 5 | 14 | +0.04R | 1.04 | nearly flat |
| poor_pullback_structure | 27 | 9 | 18 | +0.41R | 1.48 | weaker than baseline |

Interpretation:

```text
BUY_BB_RSI30 should remain in the seven-candidate set.
But if live losses show high_volatility_chase + m15_signal_candle_large together, this candidate deserves early review.
```

---

### 4. SELL_DONCHIAN96 variants

The Donchian96 variants are the weakest part of the seven-candidate set.
The AI tags suggest late breakdown / chase behavior around large M15 candles and prior low areas.

CD60 important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| m15_signal_candle_large | 24 | 3 | 21 | -0.43R | 0.53 | strongest CD60 bad tag |
| poor_pullback_structure | 7 | 1 | 6 | -0.35R | 0.62 | small but weak |
| macd_late_signal | 15 | 3 | 12 | -0.06R | 0.93 | weak / nearly flat |
| near_recent_low | 28 | 9 | 19 | +0.47R | 1.65 | common watch tag, not enough alone |

CD120 important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| macd_late_signal | 12 | 2 | 10 | -0.22R | 0.75 | strongest CD120 bad tag |
| near_recent_low | 26 | 8 | 18 | +0.40R | 1.54 | common watch tag |
| m15_signal_candle_large | 22 | 7 | 15 | +0.42R | 1.58 | not good enough for confidence |
| range_edge_entry | 30 | 10 | 20 | +0.53R | 1.76 | close to strategy baseline |

Interpretation:

```text
Do not remove Donchian96 yet because the user decided to maintain all seven candidates.
But Donchian96 should be the first family to monitor in live/backtest comparison.
The most actionable tags are m15_signal_candle_large, macd_late_signal, and poor_pullback_structure.
near_recent_low is common, but it is not sufficient by itself.
```

---

### 5. SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5

Donchian48 is more stable than Donchian96 in the sample.
The warning tags exist, but none clearly justify removal.

Important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| ema_distance_too_large | 9 | 3 | 6 | +0.39R | 1.46 | weaker than baseline |
| m15_signal_candle_large | 15 | 5 | 10 | +0.40R | 1.47 | weaker than baseline |
| near_recent_low | 12 | 5 | 7 | +0.80R | 2.08 | not a strong negative tag here |

Interpretation:

```text
Keep Donchian48 as a valid candidate.
Monitor m15_signal_candle_large and ema_distance_too_large, but do not demote yet.
```

---

### 6. SELL_KC_CCI150_LONDON_TP100_SL10

SELL_KC_CCI150 remains one of the cleaner candidates.
The main caution tag is ema_distance_too_large.

Important risk tags:

| tag | sample | wins | losses | avg R | PF | note |
|---|---:|---:|---:|---:|---:|---|
| ema_distance_too_large | 15 | 2 | 13 | +0.27R | 1.26 | weak compared with strategy sample avg |
| against_h1_context | 18 | 4 | 14 | +1.25R | 2.34 | watch but not fatal |
| m15_signal_candle_large | 21 | 6 | 15 | +1.95R | 3.28 | not a clear negative tag |

Interpretation:

```text
Keep as a main candidate.
Watch ema_distance_too_large if live losers cluster there.
```

---

## Tags to prioritize in live comparison

High priority tags:

```text
poor_pullback_structure
m15_signal_candle_large
macd_late_signal
high_volatility_chase
ema_distance_too_large
```

Medium priority tags:

```text
near_recent_low
near_recent_high
range_edge_entry
against_h1_context
against_h4_context
entry_after_extended_move
```

Low priority / caution-only tag:

```text
tp_sl_distance_invalid
```

Reason:

```text
tp_sl_distance_invalid may be triggered because several strategies intentionally use high-RR TP/SL such as TP150/SL10.
It should not be treated as a direct implementation bug unless confirmed by price-level validation.
```

---

## Current decision

Keep all seven candidates.

```text
1. SELL_KC_CCI150_LONDON_TP100_SL10
2. BUY_SWEEP_RECLAIM_RSI_TP150_SL10
3. BUY_STOCH_BB_KTURN_NY_TP150_SL10
4. SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5
5. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120
6. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60
7. BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5
```

No automatic rule change is approved from this AI review.

The AI review result should be used to:

```text
- label backtest winners/losers
- compare live tags against backtest tags
- identify repeated live failure modes
- decide later whether a tag should become a filter candidate
```

---

## Next recommended steps

### Step 1: preserve current AI review results

Do not overwrite:

```text
data/runtime_logs/trade_ai_review_backtest_gold_strict_7/trade_ai_review_ledger.jsonl
```

### Step 2: build a backtest-vs-live comparison design

Needed later:

```text
- same tag taxonomy
- same strategy_id names
- separate live and backtest output folders
- per-strategy tag frequency comparison
- per-tag live win/loss tracking
```

### Step 3: prepare Discord / guarded demo preview only after explicit approval

Do not connect directly to MT5 order send from this AI review result.

Recommended future path:

```text
GOLD strict 7 signal detection
  -> signal preview CSV
  -> Discord dry-run preview
  -> guarded demo payload preview
  -> live AI review ledger
  -> comparison against this backtest AI review
```

---

## Future-chat instruction

When continuing from this document, read these first:

```text
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
docs/REPOSITORY_CLEANUP_AND_DEPRECATION_POLICY.md
```

Then continue from one of:

```text
1. live/Discord preview design for GOLD strict 7
2. backtest-vs-live AI tag comparison design
3. BTC strict signal rebuild
4. repository cleanup/reference audit
```
