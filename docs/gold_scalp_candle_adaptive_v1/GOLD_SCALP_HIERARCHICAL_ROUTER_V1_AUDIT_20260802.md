# GOLD SCALP HIERARCHICAL ROUTER V1 — Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_HIERARCHICAL_AND_PATH_ROUTER_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`**

## User boundary

- Existing GOLD candle data only.
- Standard spread: **0.30 USD once** in the exact-M1 outcome accounting.
- Initial stop: no greater than 5 USD.
- Target: no lower than 5 USD.
- Breakeven movement allowed.
- Desired calibration frequency: at least 120 trades in 2024H2 and median at least 20 trades/month.
- Desired positive-PnL win rate: at least 50%.
- Desired PF: at least 1.20.
- At least four of six calibration months positive.

No V19 or Challenger C1 runtime state, score, rank, episode, trade, or Discord state was used as a candidate input or modified.

## Shared execution contract

- MT5 broker-server naive time.
- Closed rows only.
- Exact M1 entry and outcome resolution.
- Fixed spread 0.30 USD once.
- Recorded entry spread gate: 30 points.
- Protective stop first when target and stop are both reachable in one M1.
- One-position non-overlap.
- Nine frozen exits from the prior M1 mixture cache, including TP5–10, SL2.5–5, three breakeven variants, and two causal ATR variants.

## Vector A — hierarchical counterfactual router

The problem was decomposed into:

1. whether any side/exit was tradable;
2. LONG versus SHORT counterfactual direction;
3. side-specific exit selection.

The original full-feature 140-tree design exceeded the CPU budget before any metric. A compute-only amendment preserved all labels, periods, exits, thresholds, and gates while reducing the model width and using the fixed 50-column event/HTF static feature set.

Diagnostics:

- 2024H2 tradability AUC: **0.8201**.
- 2024H2 direction AUC: **0.5615**.

No calibration row passed. Among rows meeting the frequency requirements, the strongest result was:

- n=171;
- median=33.5 trades/month;
- win rate=43.27%;
- PF=1.0555;
- net=+23.65;
- positive months=3/6.

High-confidence combinations reached high PF only by collapsing to 2–37 trades, far below the required frequency.

### Interpretation

The candle/event data had useful information about whether movement was available, but much weaker information about which direction would monetize it.

## Vector B — event-direction anchored router

Because the learned direction was weak, the original event direction was retained and AI was limited to:

- profitability filtering for that side;
- per-row exit selection.

No row passed.

The strongest descriptive row was:

- n=73;
- median=10 trades/month when all six months, including a zero month, are counted;
- win rate=52.05%;
- PF=1.6307;
- net=+90.94;
- positive months=4/6.

It failed both the 120-trade and 20-trades/month gates.

At sufficient frequency, the strongest row was:

- n=122;
- median=22 trades/month;
- win rate=40.98%;
- PF=1.1641;
- net=+48.17;
- positive months=3/6.

## Vector C — tradability AI plus first-break direction

The direction model was removed entirely. After a high tradability score, the system waited 15 or 30 minutes for the first unambiguous 0.5, 1.0, or 1.5 USD break from the decision reference, then entered in the break direction at the next M1 open.

Seven fixed/breakeven exits were tested across 210 combinations.

No row passed.

The strongest PF at sufficient frequency was:

- score P80;
- 1.5 USD trigger;
- 15-minute wait;
- TP10/SL5 with breakeven after +4;
- n=337;
- median=62.5 trades/month;
- win rate=33.23%;
- PF=1.0418;
- net=+29.85.

The highest high-frequency win rate was about 42.02%, with PF 1.0147.

## Vector D — false-break reclaim fade

Instead of following the first break, the system required price to close back through the pre-break reference within 5 or 10 minutes, then entered in the opposite direction at the next M1 open.

The base geometry tested 420 combinations. A later explicitly exploratory consensus pass added six fixed filters based on event support and H1/H4 direction, for 2,520 combinations total.

No row passed the full gate.

Closest high-frequency rows included:

1. TP10/SL5, P90, 1.5 USD break, 30-minute trigger wait, 10-minute reclaim:
   - n=140;
   - median=25.5 trades/month;
   - win rate=47.86%;
   - PF=1.2116;
   - net=+68.51;
   - positive months=4/6.

2. TP7.5/SL3.5, P95, 1.0 USD break, 15-minute wait, 10-minute reclaim:
   - n=124;
   - median=20.5 trades/month;
   - win rate=45.16%;
   - PF=1.3250;
   - net=+68.09;
   - positive months=5/6.

3. Highest win rate among rows meeting frequency:
   - n=120;
   - median=23 trades/month;
   - win rate=48.33%;
   - PF=1.1489.

Consensus filters improved some sparse rows substantially, but no filtered row retained 120 trades, 20/month, 50% win rate, and PF 1.20 simultaneously.

## Evaluation-access audit incident

The scripts correctly prevented 2025+ trade-ledger evaluation unless the calibration gate passed. However, the diagnostic code also calculated 2025+ model AUC automatically.

Therefore:

- no 2025+ trade PnL, PF, win-rate, or threshold selection was opened;
- but 2025+ labels were touched for AUC diagnostics;
- the AUC values were not used to choose any condition;
- these vectors must nevertheless be treated as **retrospective exploratory research**, not a pristine untouched evaluation sequence.

Future scripts must omit all evaluation-label diagnostics until a calibration gate passes.

## Formal conclusion

`RETROSPECTIVE_HIERARCHICAL_AND_PATH_ROUTER_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`

The strongest new conclusion is structural:

- predicting **whether the next path is tradable** is materially easier than predicting direction;
- direct direction models, first-break following, and false-break fading did not reach 50% win rate at the required frequency;
- false-break fade is the closest high-frequency family, but remains below the user requirement and must not be rescued by threshold interpolation or post-result hour/month/volatility deletion.

## Prohibitions

- Do not interpolate a threshold between P90 and P95 after seeing these results.
- Do not delete months, directions, exits, or volatility bands to force 50%.
- Do not open a Shadow or Discord notifier.
- Do not connect MT5 orders or live trading.
- Do not modify frozen V19 or Challenger C1.

## Next materially distinct research boundary

A future candle-only study should avoid another binary win classifier. A more distinct candidate is a **first-passage distribution model** that estimates the probability and expected time of reaching +5…+12 and −2…−5 barriers jointly, then abstains when the directional first-passage distributions overlap. This should be preregistered as a new study rather than used to rescue the present rows.
