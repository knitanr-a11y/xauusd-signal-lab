# BTC AI V1 — OHLC Event-Anchored Trajectory and Survival Forensic Result

Date: 2026-08-03  
Status: `COMPLETE_MATCHED_BASELINE_NO_FORENSIC_SUPPORT_SURVIVOR`

## Authority

- accepted XM `BTCUSD#` closed-bar OHLC only
- MT5 broker-server naive time
- no external data and no volume features
- analysis period: 2024-01 through 2025-12, exactly 24 calendar months
- 2026 remained unopened
- this stage did not rank candidate PnL

## Preregistered anchor families

1. 20-bar range break
2. causal 20-bar swing turn
3. expansion after compression
4. named phase-transition start
5. failed 20-bar range break
6. EMA20 slope zero-cross turn

All anchors were generated from information available at the closed M15 anchor bar. Events required 96 contiguous historical M15 bars and 32 contiguous future M15 bars. No gaps were filled.

## Survival outcome

For each directed anchor:

- continuation: +1.00 ATR in the anchor direction first;
- reversal: -0.75 ATR first;
- same-bar collision: reversal first;
- censor: neither barrier within 32 M15 bars.

The event registry contained:

- 28,355 directed anchor events;
- six anchor families;
- 15 anchor subtypes;
- exactly 24 calendar months.

## Detected design flaw and correction

The first raw analysis reported 13 subtypes passing the preregistered raw rate-separation gates. That intermediate result is invalid.

Because the continuation barrier was 1.00 ATR while the reversal barrier was only 0.75 ATR and same-bar collisions were reversal-first, reversal dominance was structurally likely even without an anchor. Raw continuation-minus-reversal was therefore not evidence of anchor information.

Before calculating a corrected result, a uniform matched-baseline correction was frozen:

- match by half-year;
- D1 UP / NEUTRAL / DOWN;
- maturity-distance bin;
- direction;
- use the identical barriers and collision rule;
- exclude exact timestamp/direction rows belonging to the evaluated subtype.

The raw support count of 13 is void and must not be cited.

## Corrected aggregate result

- anchor subtypes evaluated: 15
- corrected forensic support survivors: **0**
- candidate PnL opened: no
- 2026 opened: no

No subtype simultaneously met:

- at least 160 events;
- at least 25 events in every half-year;
- at least 18 active months;
- at least 80 non-censored outcomes;
- absolute matched incremental outcome separation of at least 5 percentage points;
- the same incremental direction in all four half-years;
- the same incremental direction in at least two D1 regimes;
- maximum half-year event concentration of 45%.

## Largest corrected effects

`outcome difference` equals continuation rate minus reversal rate. `incremental` is anchor outcome difference minus its matched ordinary-M15 baseline.

| Anchor subtype | Events / 24m | Events/month | Observed diff | Matched baseline | Incremental | All 4 half-years same sign | Corrected pass |
|---|---:|---:|---:|---:|---:|---|---|
| `COMPRESSION_EXPANSION_DOWN` | 128 | 5.33 | -0.2656 | -0.1476 | **-0.1180** | yes | no — insufficient density |
| `EARLY_TO_MATURE` transition | 161 | 6.71 | -0.2050 | -0.1575 | -0.0474 | no | no |
| `RANGE_BREAK_20_DOWN` | 2,828 | 117.83 | -0.1779 | -0.1397 | -0.0382 | no | no |
| `RANGE_BREAK_20_UP` | 3,237 | 134.88 | -0.1980 | -0.1648 | -0.0332 | yes | no — below 5-point gate |
| `COMPRESSION_EXPANSION_UP` | 133 | 5.54 | -0.1278 | -0.1576 | +0.0297 | no | no — sparse and unstable |
| `EMA20_SLOPE_TURN_DOWN` | 1,488 | 62.00 | -0.1821 | -0.1531 | -0.0290 | no | no |
| `FAILED_DOWN_BREAK -> UP` | 1,916 | 79.83 | -0.1461 | -0.1669 | +0.0207 | yes | no — effect too small |

## Time and regime findings

### Downward expansion after compression

`COMPRESSION_EXPANSION_DOWN` had the largest incremental reversal effect, but only 128 events over 24 months.

Half-year incremental outcome difference:

- 2024H1: -0.3408, 15 events
- 2024H2: -0.1306, 34 events
- 2025H1: -0.0310, 35 events
- 2025H2: -0.1016, 44 events

The sign was stable but magnitude varied greatly and the first half-year had only 15 observations.

D1 incremental effect:

- D1 DOWN: -0.1764, 30 events
- D1 NEUTRAL: -0.2372, 39 events
- D1 UP: -0.0096, 59 events

The effect was nearly absent in D1-UP conditions.

### Failed downside break followed by upward return

`FAILED_RANGE_BREAK_20_UP_AFTER_FAILED_DOWN` had a small positive incremental effect in all four half-years:

- +0.0270
- +0.0113
- +0.0214
- +0.0230

It completed 1,916 events over 24 months, or 79.83 per month, but the effect was only +2.07 percentage points versus the frozen +5-point requirement. It is a stable weak signal, not a supported anchor.

### Range breaks

Both up and down 20-bar breaks had more reversal-first outcomes than their matched baselines.

- DOWN break incremental difference: -0.0382
- UP break incremental difference: -0.0332

The DOWN break effect changed sign in 2025H1 and differed by D1 regime:

- D1 DOWN: +0.0571
- D1 NEUTRAL: -0.0426
- D1 UP: -0.0904

A generic breakout continuation or generic breakout fade rule is therefore not invariant.

## Anchors predict magnitude better than direction

The clearest anchor information was in future excursion magnitude and path turbulence, not continuation direction.

At four M15 bars after the anchor, versus matched baseline:

| Anchor | Incremental MFE | Incremental MAE | Incremental directional close displacement |
|---|---:|---:|---:|
| `COMPRESSION_EXPANSION_UP` | **+1.0160 ATR** | +0.4427 ATR | +0.3284 ATR |
| `COMPRESSION_EXPANSION_DOWN` | **+0.7274 ATR** | +0.5155 ATR | +0.1287 ATR |
| `RANGE_BREAK_20_DOWN` | +0.4290 ATR | +0.1722 ATR | +0.0691 ATR |
| `MATURE_TO_EXHAUSTION` transition | +0.3821 ATR | +0.1638 ATR | +0.0432 ATR |

At eight M15 bars, expansion anchors also produced approximately +0.82 to +0.87 ATR more pullback than matched ordinary states.

Therefore compression-expansion is a reliable **volatility and two-sided excursion anchor**, but not a reliable fixed-direction entry anchor under the frozen barriers.

## Relation to the 2026 failure root cause

This forensic supports the prior root-cause conclusion:

- a break or expansion does not have one invariant directional meaning;
- the same anchor behaves differently by D1 state and time period;
- general models can identify increased future movement but cannot reliably order fixed directional payoff;
- late-entry failure is partly an anchor-age and path-shape problem, not simply a missing trend sign.

## Formal conclusion

`EVENT_ANCHORS_EXPLAIN_EXCURSION_MAGNITUDE_BUT_NO_PREREGISTERED_ANCHOR_HAS_STABLE_INCREMENTAL_DIRECTIONAL_SURVIVAL_EDGE`

Formal supported candidates remain **0**.

No gate was relaxed. No sparse pattern was rescued. Candidate PnL, robustness and 2026 were not opened.

## Next stage

`BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_CONDITIONAL_MODEL_PREREGISTRATION`

A subsequent stage may model, for all anchor families uniformly:

- bars since anchor;
- directional ATR distance from anchor;
- MFE already achieved;
- pullback from the post-anchor extreme;
- acceptance or rejection after the anchor;
- D1/H4 state;
- conditional continuation versus reversal hazard.

It must compare magnitude prediction separately from directional prediction, retain all anchor families, and require transfer across half-years and D1 regimes before any exact-M1 PnL shortlist.
