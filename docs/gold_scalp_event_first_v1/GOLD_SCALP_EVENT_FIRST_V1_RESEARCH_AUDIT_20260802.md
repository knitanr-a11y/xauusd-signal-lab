# GOLD SCALP EVENT-FIRST V1 — Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_EVENT_FIRST_RESEARCH_COMPLETE_PROVISIONAL_DAILY_REOPEN_GAP_LONG_AI_LEAD_NO_DEPLOYMENT`**

## Executive conclusion

A broad event-first GOLD scalping study was completed after the broad every-M5 classifier failed. The study deliberately included ordinary and unusual hypotheses: run exhaustion and continuation, alternating-bar explosions and fakeouts, sweep/reclaim, inside/outside/engulf patterns, volume climax and absorption, wick pressure, EMA snapback/escape, 0.25/1/5/10 USD price grids, hour and weekday rules, M5 gaps, all 16 four-bar direction motifs in follow/fade form, arbitrary parity placebos, event confluence, full event inversion, 100 deterministic random rules, delayed/pullback/confirmation entries, direction-specific candidates and event-local AI.

Most paths failed. One small provisional lead remained:

`REOPEN_GAPDOWN_RECLAIM_LONG_G0.25_R0.25 + LIGHTGBM_SMALL + TP5_SL3_H120 + 2024H2_P50`

It produced 16 selected trades from 2025 onward, 11 positive-PnL wins, 68.75% win rate, PF 3.4407, net +36.61 USD and DD 3.00 USD. It is not deployable because the sample is small, the lead was found after extensive retrospective research, the event is concentrated at the daily session restart, and no supporting 2026H1 sample exists.

## Time and execution contract

- MT5 broker-server naive time;
- latest raw rows closed by contract;
- M5 decision after the bar closes;
- exact M1 entry and outcome evaluation;
- fixed spread 0.30 USD;
- recorded entry spread gate 30 points;
- same-M1 TP/SL collision resolves SL first;
- unresolved future gaps excluded;
- one-position non-overlap.

The fixed value contracts were:

1. TP5 / SL3 / 120 M1 minutes;
2. TP7.5 / SL4 / 180 M1 minutes;
3. TP10 / SL5 / 240 M1 minutes.

## Phase A — 66 event families

The first phase generated 66 event families and 1,334,782 event episode-start rows. Across the three TP/SL contracts there were 198 direct-rule combinations.

- direct preregistered rule-gate passes: 0;
- per-event AI formal calibration passes: 0.

The strongest pre-2025 rows still failed to maintain sufficient calibration stability. Four-bar motif mining and arbitrary grid/calendar ideas did not produce a complete candidate.

## Phase B — intentionally unconventional checks

The following were tested before their outcomes were calculated:

- same-side event confluence count >= 2;
- same-side event confluence count >= 3;
- agreement across >= 2 distinct event groups;
- inversion of every non-placebo/non-motif event;
- 100 deterministic pseudo-random sparse entry rules, three contracts each;
- union LightGBM across all structural event candidates;
- immediate, delay-5m, delay-15m, pullback-0.5, pullback-1.0 and breakout-close-next-open entry timing.

Results:

- confluence rule-gate passes: 0;
- inverse rule-gate passes: 0;
- deterministic random combinations: 300;
- deterministic random rule-gate passes: 0;
- union-AI formal calibration passes: 0.

The placebo pass count of zero is useful: the fixed gate was not so permissive that arbitrary 1% entry rules routinely passed.

## Phase C — LONG and SHORT as separate hypotheses

Direction-specific candidates were preregistered as independent hypotheses rather than deleting a losing side after evaluation. Four pre-2025 side-specific rows passed the fixed gate:

| Event | Side | Contract | Pre-2025 n | Pre-2025 WR | Pre-2025 PF | 2025+ n | 2025+ WR | 2025+ PF | 2025+ net |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| M5_GAP_FILL | LONG | TP10/SL5 | 220 | 51.36% | 1.202 | 66 | 45.45% | 1.346 | +60.07 |
| M5_GAP_FILL | LONG | TP5/SL3 | 225 | 49.78% | 1.213 | 70 | 47.14% | 1.336 | +36.47 |
| QUIET3_MARUBOZU | LONG | TP5/SL3 | 93 | 45.16% | 1.142 | 71 | 45.07% | 1.333 | +38.10 |
| M5_GAP_FILL | LONG | TP7.5/SL4 | 222 | 48.20% | 1.130 | 67 | 38.81% | 1.022 | +3.58 |

This exposed a LONG-side edge, but the unfiltered win rates remained below 60%.

### Side-local AI

Fixed L2 logistic and small LightGBM filters were trained through 2024H1, calibrated on 2024H2 and evaluated from 2025 onward.

Notable rows:

- M5_GAP_FILL LONG, TP5/SL3, logistic P50: calibration gate PASS; evaluation n=26, WR=57.69%, PF=2.162, net +35.37;
- M5_GAP_FILL LONG, TP7.5/SL4, logistic P70: calibration gate PASS; evaluation n=12, WR=50.00%, PF=1.385, net +9.25;
- M5_GAP_FILL LONG, TP10/SL5, logistic P50: calibration gate FAIL; evaluation n=23, WR=60.87%, PF=2.782, net +75.78.

The TP10 row was not promoted because its calibration gate failed even though its later arithmetic looked strong.

## Phase E — explicit daily-restart gap family

Inspection showed that many selected M5 gap events occurred at 01:05 MT5 server time, the first completed M5 after the observed daily session restart. A new exploratory family was fixed before calculation:

- minimum gap: 0.25 / 0.5 / 1 / 2 / 5 USD;
- first-bar response: 25% / 50% / 75% of the gap;
- gap-down reclaim LONG;
- gap-up reject SHORT;
- gap-down continuation SHORT;
- gap-up continuation LONG;
- all three TP/SL contracts.

Nineteen pre-2025 rows passed the fixed exploratory gate. Pre-2025 results often showed 60–70% win rates, but 2025+ win rates generally fell to about 43–49%.

The stronger simple 2025+ rows included:

- gap down >= 0.50, first-bar reclaim >= 75%, TP10/SL5: n=35, WR=48.57%, PF=1.703, net +60.71;
- gap down >= 0.25, first-bar reclaim >= 75%, TP10/SL5: n=47, WR=48.94%, PF=1.624, net +72.63;
- gap down >= 0.50, first-bar reclaim >= 75%, TP5/SL3: n=35, WR=45.71%, PF=1.369, net +20.09.

This indicates a possible daily-restart gap edge, but not a 60% simple rule.

## Phase F — AI inside the broad daily-restart event

The broad event was fixed as:

- decision at 01:05;
- 01:00 M5 open at least 0.25 USD below the prior completed M5 close;
- first M5 closes upward by at least 25% of the gap;
- LONG only.

Two fixed models were tested: L2 logistic and small regularized LightGBM. Thresholds were fixed from 2024H2 prediction quantiles.

The strongest complete row was:

- contract: TP5/SL3/120;
- model: small LightGBM;
- threshold: 2024H2 P50 = 0.732653477650135;
- training base-event rows: 74;
- calibration base-event rows: 25;
- evaluation base-event rows: 57;
- calibration selected: 13;
- evaluation selected: 16.

### Selected performance

| Split | n | Positive-PnL WR | TP rate | PF | Net | DD |
|---|---:|---:|---:|---:|---:|---:|
| 2024H2 calibration | 13 | 76.92% | 15.38% | 2.7385 | +12.50 | 5.98 |
| 2025+ evaluation | 16 | 68.75% | 62.50% | 3.4407 | +36.61 | 3.00 |

Period detail:

- 2025H1: 7 trades, WR 85.71%, PF 10.00, net +27.00;
- 2025H2: 8 trades, WR 62.50%, PF 2.401, net +12.61;
- 2026H1: 0 trades;
- 2026JUL: 1 trade, one loss, net -3.00.

### Cost stress

The base result already includes fixed spread 0.30. Additional per-trade cost stress produced:

- +0.30: PF 2.928, net +31.81;
- +0.60: PF 2.501, net +27.01;
- +1.00: PF 2.031, net +20.61;
- +1.50: PF 1.560, net +12.61.

### Seed robustness

Five random seeds produced evaluation win rates from 66.67% to 68.75%, PF from 3.029 to 3.441 and DD 3.00. The result was not dependent on one random seed.

### Feature ablation

- all fixed features: n=16, WR 68.75%, PF 3.441;
- no time features: n=17, WR 64.71%, PF 2.751;
- no gap-extra features: n=17, WR 64.71%, PF 2.867;
- M5/M15/time/gap only: n=17, WR 52.94%, PF 1.734;
- gap magnitude/fill ratio/event spread only: n=28, WR 42.86%, PF 1.136.

The event definition alone was insufficient. The selected result depended on broader causal context, but no single feature-set view proved a stable universal 60% classifier.

## Statistical and execution limitations

- evaluation wins: 11/16;
- Wilson 95% interval: approximately 44.4% to 85.8%;
- month-block bootstrap P(net > 0): 0.99895;
- month-block bootstrap P(WR >= 60%): 0.8077;
- evaluation AUC: approximately 0.539;
- exact-M1 independent re-evaluation: 0 PnL mismatches, 0 exit mismatches, 0 reason mismatches.

The bootstrap only resamples known historical months. It cannot represent a new market regime or live restart slippage.

## Formal decision

`PROVISIONAL_RESEARCH_LEAD_ONLY`

The lead is worth fresh prospective observation, but it is not a deployable candidate.

Prohibitions:

- do not change 01:05, gap 0.25, response 0.25, LONG, TP5, SL3 or P50 to improve history;
- do not start MT5 orders or live trading;
- do not claim 60% is established from 16 trades;
- do not merge as a validated strategy;
- do not modify frozen V19 or Challenger C1.

The only valid next step would be a separate no-backfill prospective Shadow that records all base events, scores, accepted and rejected P50 rows, actual spreads, gaps and assumed slippage. Shadow and Discord remain unauthorized until explicitly approved.
