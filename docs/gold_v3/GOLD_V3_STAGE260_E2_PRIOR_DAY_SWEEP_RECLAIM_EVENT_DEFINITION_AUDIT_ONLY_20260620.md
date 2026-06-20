# GOLD V3 Stage260 E2 Event Definition
## Prior MT5 Session High/Low Sweep and Reclaim — AUDIT ONLY

Date: 2026-06-20  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Formal parent status: `GOLD_V3_259_NORMAL_LOWVOL_SPECIALIST_SEARCH_DONE_AUDIT_ONLY`  
Working status: `GOLD_V3_260_E2_DEFINITION_LOCKED_IMPLEMENTATION_PENDING_AUDIT_ONLY`

## 1. Scope and safety

This document locks the E2 population definition before any E2 outcome is calculated.

The following remain OFF and must not be connected by this stage:

- `live_ready`
- `final_signal`
- MT5 order placement
- Discord notification
- live hook
- autotrade
- order payload generation

`NO_SIGNAL` remains a normal safe result. This stage is research/audit only and cannot promote any strategy to live use.

Isolation remains mandatory. GOLD V2, old GOLD, DISC8, Stage41 feature-only snapshots, and other quarantined trading sources must not be read, referenced, used, or used as fallback.

## 2. Time and candle contract

- Every CSV `time` field is the candle **OPEN time**.
- The newest CSV row is contractually **closed** and must not be dropped as open/as-of.
- Availability time is `open_time + timeframe`.
- M1 event confirmation is known only at `m1_open_time + 1 minute`.
- Entry evaluation begins at the first M1 open after confirmation.
- HTF inputs are eligible only when `source_close_time <= decision_time`.
- Different CSV downloads are joined by timestamp, never by row number or index.
- If TP and SL are touched in the same M1 bar, SL wins.
- MFE and MAE continue to the horizon end even when TP or SL was touched earlier.

## 3. Definition of “previous day”

“Previous day” means the immediately preceding completed MT5 trading session reconstructed from the authoritative M1 source.

A new MT5 session starts after an M1 timestamp gap greater than 15 minutes. The previous session high and low are calculated from all M1 bars in that completed session. They are fixed and fully known before the current session begins.

D1 candle timestamps are not used to create the E2 horizontal level because D1 has a known timestamp-contract caveat. D1 can be retained only as a separately audited contextual source.

## 4. Base E2 event definition

Two symmetric event directions exist.

### E2-LONG: previous-session low sweep and reclaim

1. The current session is outside the first 60 minutes after session start.
2. M1 trades below the previous-session low by at least `0.05 × causal H1 ATR14`.
3. Within 15 minutes from the first qualifying breach, an M1 candle closes back inside the previous range by at least `0.02 × causal H1 ATR14`.
4. To exclude a single isolated wick, at least one of the following must also be true before reclaim:
   - at least one M1 candle closed outside/below the previous-session low; or
   - at least two M1 bars traded outside/below the level during the breach episode.
5. Direction is LONG.
6. Event decision time is the reclaim candle close time.
7. Evaluation entry is the next available M1 open at that decision time.

### E2-SHORT: previous-session high sweep and reclaim

The definition is the exact mirror image:

1. Outside the first 60 minutes after session start.
2. M1 trades above the previous-session high by at least `0.05 × causal H1 ATR14`.
3. Within 15 minutes, an M1 candle closes back inside by at least `0.02 × causal H1 ATR14`.
4. At least one M1 outside close or at least two outside-trading bars.
5. Direction is SHORT.
6. Decision time is the reclaim candle close time.
7. Evaluation entry is the next available M1 open.

The event is not defined by a wick alone. Reclaim confirmation is mandatory in the base population.

## 5. One-setup-one-trade and duplicate handling

The raw event table keeps the first valid confirmed event for each side/previous-session level within a session.

Evaluation outputs must be separated into:

1. raw event population;
2. horizon-deduplicated population;
3. matched-control population;
4. cost and first-touch evaluation population.

For a trade-rule variant, an event is ignored while that variant is active. After resolution, the same setup cannot rearm until its event condition has returned false. No event sibling may be counted as an independent strategy merely because a nearby threshold changes.

## 6. Session and holding restrictions

The base audit horizon is 120 minutes. Sensitivity horizons are 60, 180, and 240 minutes.

A candidate is not eligible for a live-reproducible evaluation when its planned horizon crosses:

- the locked safe session end;
- an MT5 date change;
- a weekend boundary;
- a known shortened holiday session boundary.

Historical observed session end may be used to mark an outcome as incomplete, but must not be treated as information known at the entry time. Full live parity therefore requires a session schedule/calendar that was knowable before the candidate entry. Until that source is supplied and verified, holiday-shortened-session parity is explicitly unresolved and live promotion remains impossible.

## 7. Causal context recorded at decision time

The event detector records but does not initially filter on:

- penetration in dollars and ATR units;
- reclaim duration;
- outside-close flag;
- count of bars trading outside;
- M1/M5 volume if available;
- causal H1 ATR14 and ATR14/ATR50;
- causal ATR percentile band;
- locked HIGH/NORMAL/TRANSITION regime;
- MT5 weekday and server-hour bucket;
- month, quarter, and half-year;
- distance from reclaim close to the swept level;
- prior-session range and duration.

The Stage258-compatible regime timeline is an authoritative input. A new regime formula must not be invented from 2026 performance. If exact regime source parity cannot be restored, matched-control evaluation is blocked rather than silently replaced.

## 8. Matched control contract

Each true E2 event is matched to a non-event anchor with:

- same weekday;
- same MT5 server-hour bucket;
- same causal ATR band;
- same HIGH/NORMAL/TRANSITION regime;
- same direction/level side;
- same quarter, with nearest calendar date preferred;
- no confirmed E2 event at the anchor decision time;
- price near the same-side previous-session level.

The main control is causal: “no event as of the control decision time.” A stricter retrospective control that excludes any event during the later horizon may be shown only as secondary audit output because that absence is not knowable at the control entry time.

Matching is one-to-one without replacement where possible. Unmatched events remain in the raw table and the match failure count is reported; they are not silently deleted.

## 9. Fixed evaluation surface

No outcome-driven tuning is allowed before the population comparison.

Fixed horizons:

- 60 minutes
- 120 minutes (base)
- 180 minutes
- 240 minutes

Fixed TP distances:

- 5
- 10
- 15
- 20
- 25 USD

Fixed SL distances:

- 5
- 10
- 15 USD

Fixed costs:

- cost0 = 0 USD
- cost1 = 1 USD
- cost2 = 2 USD, primary decision cost
- cost3 = 3 USD, severe stress
- cost5 = 5 USD, extreme reference only

The full fixed grid is reported. A favorable cell is not promoted merely because it is the best cell.

## 10. Mandatory outcome fields

For each event/control anchor and horizon:

- full-horizon MFE;
- full-horizon MAE;
- MFE/MAE ratio;
- 5/10/15/20/25 USD reach flags and first-reach times;
- TP/SL first touch with same-M1 SL priority;
- timeout mark-to-market result;
- gross PnL and cost0/cost1/cost2/cost3/cost5 net PnL;
- recovery to entry after 2.5 USD adverse movement;
- recovery to entry after 5 USD adverse movement;
- maximum drawdown;
- maximum losing streak;
- PF and expectancy.

Aggregation must include month, quarter, LONG/SHORT, 2025 H1, 2025 H2, fixed 2026, regime, and MT5 session/hour bucket.

## 11. Placebo families

The following are mandatory and retain the same evaluation machinery:

1. event time shifts of -15, -10, -5, +5, +10, +15 minutes;
2. horizontal level shifts of -1.0, -0.5, +0.5, +1.0 ATR;
3. LONG/SHORT reversal;
4. randomized date with time/direction strata retained;
5. weekday-swapped anchor;
6. wrong-regime matching;
7. event flag replaced by equal-count random eligible anchors;
8. breach-only population with reclaim confirmation removed.

The real event must beat matched controls and placebo families. A placebo result that is equally strong is evidence against E2 specificity.

## 12. Selection and holdout contract

- 2025 H1: discovery and descriptive diagnosis only.
- 2025 H2: selection under the already locked event definition and fixed evaluation grid.
- 2026: fixed validation. No condition, threshold, direction, candidate, or sibling may be changed after looking at 2026.

2026 has already been observed during prior research and is not a pristine holdout. This limitation must be stated in every final Stage260 conclusion.

## 13. Early rejection

E2 is rejected before feature mining when any of the following holds:

- weak cost0 population expectancy;
- small event-versus-matched-control difference;
- opposite signs in 2025 H1 and H2;
- placebo performance comparable to the real event;
- profit concentrated in one quarter;
- too few events;
- collapse under neighboring fixed sensitivity values;
- only near-duplicate siblings survive;
- event-time or matching logic contains future information.

Features must not be added merely to improve appearance after a weak population result.

## 14. Pass target for proceeding, not live promotion

Primary decision cost is cost2.

Proceeding to a small-feature phase requires all of the following as a target:

- positive 2025 and fixed-2026 PnL;
- cost2 PF at least 1.30;
- cost3 PF around or above 1.00;
- cost0 gross expectancy at least 3 USD, ideally 5 USD;
- clear advantage over matched controls and placebos;
- no single-quarter dependence;
- no severe collapse at neighboring TP/SL values;
- approximately at least 20 independent events per year.

Passing these targets would only authorize further audit/shadow research. It would not authorize live signals, notifications, order payloads, or trading.
