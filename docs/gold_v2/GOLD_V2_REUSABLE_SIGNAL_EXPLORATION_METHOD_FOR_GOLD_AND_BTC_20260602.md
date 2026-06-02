# GOLD/BTC reusable signal exploration method

Created: 2026-06-02
Status: METHOD / HANDOFF DOCUMENT
Scope: Reusable process for GOLD V2 and possible BTC exploration

## 1. Purpose

This document records the current reusable signal exploration process developed during GOLD V2 work, so the same style of exploration can be applied to BTC or future GOLD rebuilds.

It explains:

```text
1. what must be read first
2. what inputs are required
3. how to avoid look-ahead / candle-time bugs
4. how origin candidates are explored
5. how TP/SL variants are swept
6. how filters are selected
7. how confluence scoring is tested
8. how walk-forward is performed
9. how regime-aware branching is handled
10. what must not be enabled before final audit
```

## 2. Required reading order

Before doing BTC or any new GOLD signal exploration, read these documents in order.

### 2.1 GOLD reset / safety context

```text
docs/gold_v2/GOLD_V2_START_HERE_AFTER_HTF_OPEN_TIME_BUG_20260602.md
```

Reason:

```text
This explains why old GOLD/DISC documents are no longer implementation source of truth.
It also records the candle-time open-time issue and runtime safety bans.
```

### 2.2 Legacy quarantine

```text
docs/gold_legacy_quarantine/README_GOLD_LEGACY_QUARANTINE_20260602.md
```

Reason:

```text
Confirms old GOLD documents are forensic-only and must not be used as runtime authority.
```

### 2.3 Current GOLD V2 state snapshot

```text
docs/gold_v2/GOLD_V2_CURRENT_STATE_ORIGIN_CONFLUENCE_20260602.md
```

Reason:

```text
Summarizes current origin candidates, confluence score audit, and current V2 state.
```

### 2.4 Confluence walk-forward audit

```text
docs/gold_v2/GOLD_V2_CONFLUENCE_WALK_FORWARD_AUDIT_20260602.md
```

Reason:

```text
Records policy-level confluence walk-forward and its limitations.
```

### 2.5 Regime and low-vol audits

```text
docs/gold_v2/GOLD_V2_REGIME_AND_LOW_VOL_TPSL_AUDIT_20260602.md
docs/gold_v2/GOLD_V2_LOW_VOL_DEDICATED_WALK_FORWARD_AUDIT_20260602.md
```

Reason:

```text
Shows why low-volatility should not simply be disabled and why dedicated low-vol candidates are better than simple TP/SL replacement.
```

### 2.6 This document

```text
docs/gold_v2/GOLD_V2_REUSABLE_SIGNAL_EXPLORATION_METHOD_FOR_GOLD_AND_BTC_20260602.md
```

Reason:

```text
Defines the reusable workflow for BTC and future GOLD work.
```

## 3. Hard safety rules

These rules apply to BTC as well as GOLD.

```text
Do not use old GOLD/DISC ledgers as implementation source of truth.
Do not assume candle time is close time.
Do not use unconfirmed higher timeframe bars.
Do not enable Discord send during exploration.
Do not enable MT5 order_send during exploration.
Do not set dispatch_ready true.
Do not call AI/API unless a separate approved AI audit phase is explicitly requested.
Do not choose rules based only on final holdout/test best scores without walk-forward.
```

## 4. Candle-time rule

MT5-style OHLC CSV time must be treated as candle open time unless proven otherwise.

For M15 signal evaluation:

```text
m15_open_time = candle time column
entry_time = m15_open_time + 15 minutes
entry_price = M15 close, unless a different explicit execution model is being tested
```

For lower timeframe path judgement:

```text
M1/M5 path bars must start at or after entry_time.
No pre-entry bar may be used for TP/SL judgement.
```

For feature confirmation:

```text
M5 feature bar is usable only if m5_open_time + 5 minutes <= entry_time.
H1 feature bar is usable only if h1_open_time + 1 hour <= entry_time.
H4 feature bar is usable only if h4_open_time + 4 hours <= entry_time.
D1 feature bar is usable only if d1_open_time + 1 day <= entry_time.
```

Current GOLD V2 intentionally avoids H1/H4/D1 as rule inputs until a confirmed-HTF audit is implemented.

BTC should follow the same rule.

## 5. Required BTC inputs

At minimum:

```text
btcusdsharp_m15.csv
btcusdsharp_m5.csv
btcusdsharp_m1.csv
```

Recommended for later confirmed-HTF audits only:

```text
btcusdsharp_h1.csv
btcusdsharp_h4.csv
btcusdsharp_d1.csv
```

Required columns, or equivalent normalized names:

```text
time
open
high
low
close
volume or tick_volume if available
```

All times must be parsed and checked for:

```text
monotonic order
duplicates
missing bars
timezone consistency
open-time interpretation
```

## 6. Feature construction principles

Use only features available at entry time.

Core M15 features:

```text
returns over multiple windows
absolute returns
ATR and true range
range compression/expansion
Donchian position and distance to recent high/low
EMA position and EMA slopes
RSI
MACD histogram and delta
ADX
wick/body features
recent trend efficiency
session/hour features if explicitly allowed
```

Core M5 features:

```text
short-term returns
M5 Donchian position
M5 range and compression
M5 RSI/MACD
M5 distance to recent high/low
short-term pullback/rebound structure
```

BTC-specific caution:

```text
BTC has 24/7 trading and weekend behavior.
Do not copy GOLD session assumptions blindly.
Create BTC-specific hour/day-of-week features.
Check weekend volatility and liquidity behavior separately.
```

## 7. Origin candidate exploration

The preferred workflow is not to start from AI tags.

Start from price behavior:

```text
1. define favorable future movement / origin event
2. create entry snapshots from confirmed M15/M5 features
3. label each candidate entry by M1/M5 first-touch outcome
4. search for rule candidates that enrich favorable outcomes
```

Example GOLD origin idea:

```text
entry after M15 close
future path reaches favorable movement before adverse movement
```

BTC equivalent should be scaled to BTC volatility.

Do not reuse GOLD dollar distances directly for BTC.

Use one of:

```text
fixed USD levels appropriate for BTC
percentage levels
ATR-normalized target/adverse thresholds
instrument-specific point/pip conversion
```

## 8. TP/SL sweep

Do not assume one TP/SL family.

For GOLD V2, the grid included:

```text
SL25, SL50, SL75, SL100, SL125, SL150
RR1, RR1.5, RR2
```

For BTC, build a BTC-scaled grid. Recommended starting forms:

```text
fixed USD grid: e.g. SL50/100/150/200/300 depending on BTC price/volatility
percentage grid: e.g. 0.05%, 0.10%, 0.15%, 0.20%
ATR grid: e.g. SL = 0.5 ATR, 0.75 ATR, 1.0 ATR; TP by RR
```

The TP/SL judgement should be:

```text
M1 first-touch if M1 exists
M5 first-touch only if M1 is unavailable
SL priority if TP and SL touch in the same bar
fixed horizon, such as 12h or 24h, explicitly recorded
```

## 9. Candidate filtering and transformation search

Do not discard low-win/high-frequency candidates too early.

A candidate can be useful if:

```text
base win rate is low
base trade count is high
base PF remains positive
base total R remains positive
```

Reason:

```text
Such candidates may contain many weak entries plus a strong subset.
Additional filters can remove losing sub-patterns and raise win rate sharply.
```

Filter search should include:

```text
M15 trend/range state
M15 distance to recent high/low
M15 wick/body context
M15 compression/expansion
M5 short-term confirmation
M5 pullback depth
M5 distance to recent high/low
M5 RSI/MACD state
session/hour/day-of-week
regime features
```

Selection must be train-first:

```text
Choose filters on train data.
Evaluate on future test fold.
```

## 10. Confluence scoring

Overlapping signals should not automatically be discarded.

Two views must be tested:

```text
strict global no-overlap:
  any open position blocks all other signals

confluence score:
  overlapping signals are grouped into clusters
  same-direction agreement increases score
  different origins can indicate stronger independent confirmation
```

Confluence dimensions:

```text
same_direction_count
unique_origin_count
score_sum
same_direction_only / no_conflict flag
representative signal score
stacked unit-lot proxy
```

Runtime-safe interpretation:

```text
representative mode is safer
capped2/capped3 stacking can be tested
uncapped stacking is not runtime safe
```

## 11. Regime-aware branching

Do not classify a month after the fact and use that as runtime logic.

Regime must be classified at entry time from confirmed historical features.

Prototype regimes:

```text
LOW_VOL_RANGE
MID_MIXED
HIGH_VOL_TREND
HIGH_VOL_CHOP
UNKNOWN
```

Features:

```text
ATR percentile from train distribution
true-range percentile
recent range percentile
trend efficiency
ADX
recent return / directionality
```

Train/test rule:

```text
For each fold, fit regime thresholds on train months only.
Apply fixed thresholds to the next test month.
```

Current GOLD finding:

```text
Low-vol should not simply be disabled.
Low-vol should get dedicated candidates/policies.
High-vol does not currently need a separate candidate branch because baseline candidates already work well there.
```

BTC must verify this independently.

## 12. Walk-forward requirements

At minimum, run these stages:

### 12.1 Policy-level walk-forward

```text
Use existing candidate universe.
Select confluence policy on train months.
Test next month.
```

### 12.2 Candidate-universe walk-forward

```text
Use existing candidate/filter universe.
Select rules, TP/SL, and confluence policy on train months.
Test next month.
```

### 12.3 Full raw rebuild walk-forward

Most strict and preferred before runtime:

```text
For every fold:
  rebuild origin candidates from raw features using train only
  choose TP/SL using train only
  choose filters using train only
  choose confluence policy using train only
  test next month
```

This is heavier and should be implemented as an optimized repository script.

## 13. Required outputs

For every exploration phase, save outputs with clear names.

Recommended outputs:

```text
input_audit.csv
feature_health.csv
candidate_rules_all.csv
candidate_rules_selected.csv
rule_eval.csv
trade_ledger_raw.csv
trade_ledger_nonoverlap.csv
monthly_summary.csv
strategy_summary.csv
filter_shortlist.csv
transformation_candidates.csv
confluence_cluster_ledger.csv
confluence_cluster_members.csv
policy_summary.csv
walk_forward_fold_summary.csv
selected_rules_by_fold.csv
selected_policy_by_fold.csv
combined_portfolio_summary.csv
drawdown_loss_streak_summary.csv
summary.json
```

Every summary should include:

```text
input files
row counts
date range
entry model
path timeframe
TP/SL grid
horizon
SL priority rule
whether AI/API was used
whether Discord/MT5 was touched
success criteria
stop conditions
```

## 14. Minimum success criteria before demo runtime

Do not proceed to demo runtime unless all are met:

```text
No candle-time ambiguity remains.
M1/M5 first-touch audit is documented.
Walk-forward is positive after candidate-universe or raw rebuild selection.
Monthly collapse is understood.
Max loss streak is acceptable.
Stack cap is defined.
Direction conflict handling is defined.
Regime branch is documented.
Selected rules are written to stable config.
Runtime dry-run audit has zero dispatch/order calls.
```

Suggested numerical targets are context-dependent, but for a first demo candidate:

```text
walk-forward PF > 1.3 after conservative assumptions
win rate acceptable for RR profile
monthly trade count not excessive
no single cluster can exceed max allowed risk
max loss streak within account tolerance
```

## 15. Runtime risk policy draft

For confluence systems:

```text
no uncapped stacking
max stack count 2 or 3 initially
same-direction only
opposite-direction cluster means no trade or representative-only trade
low-vol uses dedicated branch or stricter confluence
high-vol can use normal branch unless future audit says otherwise
```

## 16. AI tag usage

AI tags are optional and should not be the first source of truth.

Preferred order:

```text
1. numeric exploration from OHLC
2. deterministic features and filters
3. walk-forward validation
4. optional AI tag overlay for explanation or final veto only
```

If AI is used later:

```text
AI input snapshots must come from the selected trade ledger.
AI must not re-create entries from OHLC.
AI output must be audited against source trade IDs.
API calls must be explicitly approved.
```

## 17. BTC-specific notes

BTC exploration should not simply copy GOLD thresholds.

BTC requires:

```text
BTC-scaled TP/SL grid
weekend/session behavior audit
spread/slippage assumption check
higher volatility outlier handling
exchange/CFD broker symbol precision check
24/7 day-of-week features
```

BTC regime may need:

```text
weekday/weekend split
Asia/Europe/US time split
funding/event spike awareness if relevant
```

## 18. Recommended next BTC workflow

When BTC files are ready:

```text
1. input audit
2. M15/M5/M1 feature build
3. origin event definition using BTC-scaled distances
4. TP/SL grid sweep
5. candidate/filter exploration
6. transformation candidate search
7. strict no-overlap portfolio audit
8. confluence scoring
9. candidate-universe walk-forward
10. regime-aware split
11. low-vol dedicated branch only if needed
12. full raw rebuild walk-forward script if results remain promising
```

## 19. Current final reminder

This document is a method document, not a runtime approval.

Current runtime status remains:

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI/API: not used unless explicitly approved
```
