# GOLD SCALP PATH-SHAPE NEIGHBORS V1 — Consolidated Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_PATH_SHAPE_MULTI_REPRESENTATION_COMPLETE_NO_FORMAL_CANDIDATE`**

## Contract

The study used only the existing GOLD candle data.

- MT5 broker-server naive time and closed rows only;
- exact M1 outcome resolution;
- standard spread 0.30 USD once;
- initial SL no greater than 5 USD;
- TP no lower than 5 USD;
- breakeven movement allowed;
- protective-stop-first same-M1 handling;
- structural events proposed the initial side;
- historical path neighbors decided follow, fade or abstain;
- global one-position non-overlap;
- no target-block threshold tuning or post-result hour/month deletion.

The representation was trained or standardized using **2023H1 only** and never used trade outcomes. Pseudo-forward targets began at 2024H2 because the calibration block required at least two fully prior half-year eras for neighbor agreement.

## Shared sample

- structural event rows: 170,664;
- unique valid entry/structural-side path pairs: 110,863;
- preceding path length: 60 contiguous M1 bars;
- historical eras: half-year blocks;
- neighbors were drawn separately from each fully prior era and era statistics received equal weight.

Eight exact exit policies were available in the cross-event diagnostic. The win-rate-priority studies were limited to three TP5 policies on each of follow and fade:

- TP5 / SL2.5;
- TP5 / SL3;
- TP5 / SL3 with breakeven after +2.

## Vector A — linear reconstruction representation

The preceding 60 M1 bars were canonicalized in the structural-event direction. Channels were directional return, directional body, range, favorable wick, adverse wick, directional close location, causal tick-volume z-score and causal spread z-score.

A 16-dimensional PCA representation was fitted on 2023H1 only. It explained 22.30% of standardized input variance.

### Cross-event neighbors

Historical neighbors could come from any structural event. Era-balanced expected PnL selected follow/fade and one of eight exits.

After correction of the neighbor-count selection incident described below, no calibration profile passed in any of five target sequences.

The strongest descriptive calibration row at meaningful frequency occurred in 2025H2 calibration for target 2026H1:

- 334 trades;
- WR 39.82%;
- PF 1.2035;
- net +162.00 USD;
- median 57.5 trades/month;
- four positive months.

It failed the required 50% win rate and was not opened as a target candidate.

### Same-event win-rate consensus

Neighbors were restricted to the same structural event. Selection prioritized minimum-era and average-era positive-PnL rate, and only TP5 policies were allowed.

A calibration pass appeared for target 2024H2:

- calibration 2024H1: 113 trades;
- WR 54.87%;
- PF 1.6783;
- net +87.76 USD;
- DD 14.73 USD;
- six positive months;
- median 19 trades/month.

The frozen 2024H2 target produced only three trades and all three lost:

- WR 0%;
- PF 0;
- net -9 USD.

The historical multi-era analog set therefore failed both frequency and quality immediately after calibration.

## Vector B — outcome-independent denoising autoencoder

The same 480 standardized path inputs were compressed by a small denoising autoencoder:

- input 480;
- hidden 128 and 48;
- latent 24;
- training data 2023H1 only;
- no trade labels;
- best chronological validation reconstruction MSE: 0.7412.

Same-event, multi-era TP5 win-rate consensus was then repeated.

One catalog calibration pass appeared:

- calibration 2025H2 for target 2026H1;
- 25 trades;
- WR 60.00%;
- PF 2.50;
- net +45 USD;
- DD 10 USD;
- four positive months;
- median 4 trades/month.

The frozen 2026H1 target produced:

- 15 trades;
- WR 26.67%;
- PF 0.6061;
- net -13 USD;
- DD 18 USD.

Nonlinear reconstruction did not preserve the analog outcome relationship.

## Vector C — deterministic multi-scale path geometry

Representation learning was removed. A fixed 40-dimensional path descriptor used:

- twelve consecutive 5-minute directional-return bins;
- cumulative directional movement at 5, 10, 15, 20, 30, 40, 50 and 60 minutes;
- directional efficiency at 5, 15, 30 and 60 minutes;
- range mean and standard deviation at the same horizons;
- favorable-minus-adverse wick balance;
- causal volume-z means.

The descriptor was standardized on 2023H1 only. Same-event, multi-era TP5 consensus was repeated.

One catalog calibration pass appeared:

- calibration 2025H2 for target 2026H1;
- 42 trades;
- WR 52.38%;
- PF 1.8092;
- net +47.74 USD;
- DD 28.76 USD;
- four positive months;
- median 7 trades/month.

The frozen 2026H1 target produced:

- 8 trades;
- WR 12.50%;
- PF 0.2381;
- net -16 USD;
- DD 21 USD.

The hand-defined temporal geometry also reversed after calibration.

## Implementation incident and correction

The first cross-event selection pass correctly computed and stored separate nearest-neighbor summaries for k=5, 10 and 20. However, the configuration-selection function initially did not filter the saved table to the requested k. Rows from all three neighbor counts were mixed and deduplicated.

The defect was detected during result review because several k configurations produced identical metrics. Selection and evaluation were rerun from the saved neighbor summaries with the required `k == requested_k` filter.

- no outcome labels or thresholds were changed;
- nearest-neighbor calculations were not altered;
- only corrected results are formal;
- the uncorrected zero-pass output is not used as evidence.

## Candidate-promotion conclusion

The path-shape studies produced three apparently strong calibration configurations, but their immediately following frozen targets were:

- PCA same-event: 3 trades, 0 wins;
- autoencoder same-event: 15 trades, WR 26.67%, PF 0.6061;
- multi-scale same-event: 8 trades, WR 12.50%, PF 0.2381.

None produced a positive target block. Therefore no path-shape engine is eligible for one-block or two-block candidate promotion, and no component is added to the active candidate stack.

## Formal conclusion

**`NO_FORMAL_CANDIDATE`**

Continuous path matching was materially different from named candle patterns and event-sequence grammars, but it did not solve cross-period instability. Similar paths from multiple historical eras did not retain the same follow/fade outcome relationship in the next half-year.

Do not restore the attractive calibration rows, loosen the neighbor-consensus thresholds after seeing the target, or keep only the few target events that happened to win.

## Next materially distinct boundary

A future candle-only study should stop entering at the structural-event onset. A distinct hypothesis is a **causal activation-and-retest execution layer**:

1. record an event as a setup only;
2. require price to travel 1–3 USD in the proposed direction before activation, without first breaching a fixed adverse allowance;
3. do not enter on the initial movement;
4. wait for a causal pullback or retest of a frozen activation level;
5. enter only after reclaim or renewed expansion;
6. separately test failed activation as a fade setup;
7. evaluate each activation/retest grammar through sequential half-year pseudo-forward and candidate promotion.

This changes the information available at entry rather than attempting another representation of the same event-onset state.

No Shadow, Discord, MT5 order, live trading, promotion or merge authorization follows. Frozen V19 and Challenger C1 were not modified, stopped, reconfigured or used as candidate inputs.
