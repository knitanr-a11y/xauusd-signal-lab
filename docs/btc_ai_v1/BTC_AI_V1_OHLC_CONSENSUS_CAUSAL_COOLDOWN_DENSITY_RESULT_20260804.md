# BTC AI V1 — Stage 35 causal cooldown density result

Date: 2026-08-04

Formal status:

`BTC_AI_V1_OHLC_CONSENSUS_CAUSAL_COOLDOWN_NO_SUPPORTED_CONFIGURATION`

## Causal contract

For each half-life and direction, consensus events were processed chronologically. An event was accepted only when its decision time was at least 1, 4 or 12 hours after the last accepted event. Selection used timestamps and prior accepted state only; labels were not used.

- 4 half-lives × 2 directions × 3 cooldowns × 24 months = 576 monthly records;
- causal selection violations: 0;
- cooldown carried across month boundaries;
- PnL and 2026 remained unopened.

## Results

| Half-life | Direction | Cooldown | Median monthly events | Months ≥10 | Mean suppression | Lift change vs raw consensus | Positive improvement months | Result |
|---|---|---:|---:|---:|---:|---:|---:|---|
| EXP_DECAY_HL12M | LONG | 1h | 51.0 | 20 | 0.624 | -0.0215 | 11 | FAIL |
| EXP_DECAY_HL12M | LONG | 4h | 19.0 | 18 | 0.807 | -0.0055 | 11 | FAIL |
| EXP_DECAY_HL12M | LONG | 12h | 10.5 | 15 | 0.854 | -0.0255 | 10 | FAIL |
| EXP_DECAY_HL12M | SHORT | 1h | 40.5 | 22 | 0.579 | -0.0138 | 13 | FAIL |
| EXP_DECAY_HL12M | SHORT | 4h | 19.0 | 18 | 0.778 | -0.0189 | 12 | FAIL |
| EXP_DECAY_HL12M | SHORT | 12h | 12.5 | 17 | 0.842 | -0.0265 | 8 | FAIL |
| EXP_DECAY_HL24M | LONG | 1h | 61.5 | 22 | 0.657 | -0.0054 | 7 | FAIL |
| EXP_DECAY_HL24M | LONG | 4h | 22.0 | 19 | 0.853 | -0.0120 | 10 | FAIL |
| EXP_DECAY_HL24M | LONG | 12h | 12.0 | 18 | 0.901 | -0.0172 | 10 | FAIL |
| EXP_DECAY_HL24M | SHORT | 1h | 47.5 | 23 | 0.598 | -0.0191 | 9 | FAIL |
| EXP_DECAY_HL24M | SHORT | 4h | 21.5 | 21 | 0.808 | -0.0468 | 8 | FAIL |
| EXP_DECAY_HL24M | SHORT | 12h | 13.5 | 18 | 0.868 | -0.0466 | 10 | FAIL |
| EXP_DECAY_HL3M | LONG | 1h | 10.0 | 12 | 0.569 | -0.0209 | 9 | FAIL |
| EXP_DECAY_HL3M | LONG | 4h | 6.5 | 10 | 0.711 | -0.0593 | 8 | FAIL |
| EXP_DECAY_HL3M | LONG | 12h | 5.0 | 6 | 0.764 | -0.0962 | 6 | FAIL |
| EXP_DECAY_HL3M | SHORT | 1h | 10.5 | 13 | 0.506 | -0.0256 | 9 | FAIL |
| EXP_DECAY_HL3M | SHORT | 4h | 6.0 | 8 | 0.661 | -0.0626 | 8 | FAIL |
| EXP_DECAY_HL3M | SHORT | 12h | 5.0 | 6 | 0.706 | -0.0730 | 8 | FAIL |
| EXP_DECAY_HL6M | LONG | 1h | 29.0 | 20 | 0.631 | -0.0080 | 9 | FAIL |
| EXP_DECAY_HL6M | LONG | 4h | 12.5 | 14 | 0.815 | -0.0215 | 10 | FAIL |
| EXP_DECAY_HL6M | LONG | 12h | 7.0 | 10 | 0.870 | -0.0501 | 6 | FAIL |
| EXP_DECAY_HL6M | SHORT | 1h | 22.0 | 18 | 0.534 | +0.0060 | 14 | FAIL |
| EXP_DECAY_HL6M | SHORT | 4h | 12.0 | 15 | 0.726 | -0.0119 | 13 | FAIL |
| EXP_DECAY_HL6M | SHORT | 12h | 8.0 | 10 | 0.780 | +0.0177 | 12 | FAIL |

## Findings

- 1h cooldown removed roughly 50–66% of raw consensus events; 4h removed roughly 66–85%; 12h removed roughly 71–90%.
- Most cooldown configurations reduced mean label lift rather than improving it.
- The largest positive mean lift change was HL6M SHORT with 12h cooldown at +0.01766, below the frozen +0.02 requirement; it had only 12 positive-improvement months and only 10 months with at least 10 events.
- No same half-life/cooldown passed LONG and SHORT.

## Formal conclusion

Adjacent M15 repeats do inflate raw event counts, but the repeated observations carry useful label information on average. Removing them with a live-causal cooldown reduces density and generally does not improve ordering quality.

Supported configurations: 0. Candidate PnL, 2026, Shadow, Discord, MT5 orders, live-ready and final signal remain OFF.
