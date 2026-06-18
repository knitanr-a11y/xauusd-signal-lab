# GOLD V3 Stage243 - SCALP rebuild no-lookahead search spec

Status: `AUDIT_ONLY`

## Purpose

Rebuild the SCALP strategy from scratch after discovering the Stage199/Stage178 timing issue.

The new search must find entries using only information available at the actual entry decision time.

## Absolute prohibitions

- Do not read or use GOLD V2 / old GOLD / DISC8 / Stage41.
- Do not use open/as-of/latest-open candles.
- Do not treat MT5 candle `time` as close time.
- Do not use M15/H1/H4/D1 values before their candle close time.
- Do not call Discord.
- Do not call MT5 order_send.
- Do not create live payloads.
- Do not enable autotrade.
- Do not notify on NO_SIGNAL.

## Time contract

All MT5 candle timestamps are candle open times.

Therefore:

| Timeframe | usable close_time |
|---|---|
| M1 | `time + 1 minute` |
| M5 | `time + 5 minutes` |
| M15 | `time + 15 minutes` |
| H1 | `time + 1 hour` |
| H4 | `time + 4 hours` |
| D1 | `time + 1 day` |

For any signal timeframe `S`:

```text
signal_close_time = signal_open_time + timeframe_delta(S)
entry_time = signal_close_time
entry_price = first M1 open at or after entry_time
```

For upper timeframes:

```text
HTF feature can be used only if HTF.close_time <= signal_close_time
```

This means H1/H4/D1 open-time rows are not available until the full H1/H4/D1 candle has closed.

## Outcome contract

- Outcome is checked on M1 bars after entry.
- Entry bar is included because entry price is the M1 open at/after `entry_time`.
- If TP and SL are both touched inside the same M1 bar, SL wins.
- Use fixed USD TP/SL.
- Report raw, cost3, and stress cost5.

## Search goal

Target profile:

```text
Win rate: 50% to 60% preferred, up to about 65% acceptable
RR: 1.5 to 3.0+
Trade count: increased by stacking independent candidates
Primary metric: test PF after cost3
Stress metric: test PF after cost5
```

## Split contract

- Train: 2025-01-02 <= entry_time < 2026-01-01
- Test: entry_time >= 2026-01-01
- June review: entry_time >= 2026-06-01
- Recent review: entry_time >= 2026-06-15

## Candidate families

Search independently by signal timeframe:

- M1 signal -> M1-close entry
- M5 signal -> M5-close entry
- M15 signal -> M15-close entry

Use only closed features from signal TF and closed upper TF.

## Output requirements

Stage243 must write:

- `stage243_candidate_results.csv`
- `stage243_top_candidates.csv`
- `stage243_portfolio_preview.csv`
- `stage243_no_lookahead_audit.csv`
- `stage243_summary.json`
- `paste_me.txt`

## Interpretation rule

No candidate is deployable from Stage243 alone. Stage243 only produces audit candidates for later review.
