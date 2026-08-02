# START HERE — GOLD SCALP CANDIDATE STACK V1

Date: 2026-08-02  
Branch: `feature/gold-scalp-candidate-stack-v1-research`

## Formal status

`RETROSPECTIVE_CANDIDATE_STACK_CALIBRATION_PASS_FORWARD_FAIL_NO_FORMAL_PORTFOLIO`

## Purpose

This study tested the user's proposal to combine several lower-frequency GOLD scalping candidates instead of requiring one engine to produce at least 20 trades per month.

The portfolio allowed at most one candidate from each independent family, removed same-entry duplicates, and enforced global one-position non-overlap.

## User boundary

- existing GOLD candle data only;
- standard spread 0.30 USD once;
- initial SL no greater than 5 USD;
- TP no lower than 5 USD;
- breakeven allowed;
- exact M1 outcome resolution.

## Main result

The frozen 2024H2 candidate stack reached:

- 130 trades;
- median 20.5 trades/month;
- win rate 55.38%;
- PF 2.0562;
- net +238.22 USD;
- DD 23.91 USD;
- six of six positive months.

The same frozen portfolio failed from 2025 onward:

- 1,474 trades;
- win rate 32.50%;
- PF 0.9189;
- net -379.50 USD;
- DD 515.31 USD.

Rolling 60-day ranks, semiannual retraining, and additional false-break quality/retest filters did not restore stability.

## Decision

`NO_FORMAL_PORTFOLIO`

Candidate stacking remains the preferred architecture, but historical selection is insufficient to validate a combined portfolio. Retain a frozen candidate catalog and add only independently preregistered candidates. Do not re-optimize old thresholds to force a pass.

## Authoritative read order

1. `docs/gold_scalp_candidate_stack_v1/GOLD_SCALP_CANDIDATE_STACK_V1_AUDIT_20260802.md`
2. `config/gold_scalp_candidate_stack_v1/formal_status_20260802.json`
3. `config/gold_scalp_candidate_stack_v1/candidate_catalog_20260802.csv`
4. `docs/gold_scalp_candidate_stack_v1/REPRODUCTION_NOTE_20260802.md`

## Isolation and authorization

Frozen V19 and Challenger C1 were not modified, stopped, reconfigured, or used as candidate inputs.

Research only. No Shadow, Discord, MT5 order, live trading, promotion, or merge authorization.