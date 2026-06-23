# GOLD V3 Stage309 — Stage307 Top Research Candidate Registration

## Decision

Register the Stage307 leaderboard rank-1 ensemble as an audit-only research candidate for integrated replay.

Candidate ID:

`GOLD_V3_STAGE307_TOP_REV_LONG_ANY_P90`

Ensemble:

`DROP_H4 + DROP_D1 + ALL_TF + LTF_ONLY | ANY_P90`

The candidate fires when any one of the four selected model percentile scores is at least 0.90.

## Execution contract

- Closed H4 DOWN context.
- LONG reversal candidate.
- Within 60 minutes, an M5 close must break the prior six M5 highs.
- Bullish M5 body ratio must be at least 0.20.
- Enter at the next exact M5 open.
- TP: 1.75 ATR.
- SL: 1.00 ATR.
- Maximum holding time: 360 minutes.
- M1 first-touch resolution; same-M1 SL priority.
- MT5 spread points converted with point size 0.01.

## Stage307 result being frozen

- Trades: 92
- Wins/losses: 60 / 32
- Win rate: 65.2174%
- Spread-adjusted PF: 3.3978543279816584
- Spread-adjusted total R: 48.621989738102094
- Spread-adjusted maximum DD: 4.046036473430361R
- 2025: 66 trades, +32.25759474856628R
- 2026 YTD: 26 trades, +16.364394989535818R

The candidate missed the original Stage307 balanced gate only because the minimum yearly trade count was 26 rather than 40. It passed the quality, profitability, drawdown and positive-worst-year characteristics relevant to continued research.

## Immutable source snapshot

To prevent later CSV appends from changing the selected historical result, Stage309 freezes:

- M1 latest row: `2026-06-23 13:56:00`
- M5 latest row: `2026-06-23 13:50:00`
- Context maximum: `2026-06-23 13:50:00`

The registrar recomputes the ensemble and requires exact parity at tolerance `1e-12`. Registration output is blocked if any frozen metric differs.

## Stage308 disposition

Stage308 reported zero passing families/pools. No Stage308 setup is registered at Stage309. The Stage308 outputs remain available for later rule refinement.

## Safety and promotion state

- Research candidate contract added.
- Stage292 production candidate pool not changed.
- Stage280 remains blocked.
- Stage281 unchanged.
- Stage286 unchanged.
- No live/shadow wiring yet.
- MT5 automatic order OFF.
- Discord OFF.
- Partial close OFF.

## Next stage

Stage310 will perform integrated one-position overlap, priority and drawdown replay against the existing Stage292 research candidates. Passing Stage310 will still not automatically enable production execution.
