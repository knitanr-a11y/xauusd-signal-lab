# GOLD V3 Stage247 — Quality-First 24-Slot Search

Mode: audit-only. GOLD V3 only.

## Time contract

CSV time is candle OPEN time. Availability is open time plus timeframe duration. Higher-timeframe data is usable only when its calculated close time is not later than the setup decision time. Entry is the first eligible M1 open. Same M1 bar TP/SL is counted as SL.

## Candidate library

Use eight distinct market structures, each with three entry confirmations, for a maximum of 24 auditable slots:

1. LONG trend pullback
2. SHORT trend pullback
3. LONG breakout and first retest
4. SHORT breakout and first retest
5. LONG volatility compression expansion
6. SHORT volatility compression expansion
7. LONG exhaustion or false-break reversal
8. SHORT exhaustion or false-break reversal

Entry confirmations:

A. Enter at the first M1 open after the confirmed M5/M15 setup close.
B. Wait for a subsequently closed M1 structural break, then enter at the next M1 open.
C. Wait for a subsequently closed M5 continuation or rejection candle, then enter at the next M1 open.

## Trade state

One setup equals one trade per candidate. A candidate rearms only after the trade has ended and the setup condition has become false once.

## Risk profiles

SL must be at least 2 USD and TP at least 5 USD. Primary profiles are 10/4, 15/5, 20/7.5, 25/10, 30/10, and 40/15. ATR-adaptive levels may use only ATR values known at entry.

## Quality gates

Each slot remains in the result ledger even when it fails. Passing candidates should normally have:

- at least 20 candidate-specific setup trades, or explicit low-sample status
- trades in at least three months
- cost3 PF at least 1.40 for primary watchlist
- cost5 PF at least 1.20 for primary watchlist
- no single month producing more than 55 percent of positive PnL
- neighboring thresholds and neighboring TP/SL profiles that do not collapse
- exact, 30-minute, and active-position overlap reported

Candidates with more than 30 percent overlap are grouped into the same cluster rather than counted as independent diversification.

The January–June 2026 sample has already been reviewed, so Stage247 survivors remain research/watchlist only and require future-bar validation.

Required outputs include all 24 slots, variants, monthly stability, sensitivity, overlap, cluster ledger, candidate-specific trades, no-lookahead audit, diagnostics, summary, and paste_me.
