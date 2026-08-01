# START HERE — GOLD SCALP EVENT-FIRST V1

Date: 2026-08-02  
Branch: `feature/gold-scalp-event-first-v1-research`

## Formal status

`RETROSPECTIVE_EVENT_FIRST_RESEARCH_COMPLETE_PROVISIONAL_DAILY_REOPEN_GAP_LONG_AI_LEAD_NO_DEPLOYMENT`

## Purpose

This branch records a broad event-first GOLD scalping research pass after the broad every-M5 AI study failed. It tested intentionally conventional and unconventional ideas, including runs, alternating bars, sweeps, inside/outside bars, wick and volume structures, price grids, clock/calendar rules, four-bar motifs, inverse rules, deterministic random placebos, confluence, delayed entries, direction-specific candidates and event-local AI filters.

## Provisional research lead

- event: `REOPEN_GAPDOWN_RECLAIM_LONG_G0.25_R0.25`
- decision time: 01:05 MT5 broker-server time
- event: the 01:00 M5 open is at least 0.25 USD below the previous completed M5 close, and the first M5 closes upward by at least 25% of the gap
- side: LONG only
- AI: small regularized LightGBM
- threshold: fixed 2024H2 prediction median P50 (`0.732653477650135`)
- value contract: TP5 / SL3 / 120 exact M1 minutes
- fixed spread: 0.30
- entry spread gate: 30 points
- same-M1 collision: SL first
- one-position non-overlap

Corrected selected results:

- 2024H2 calibration: 13 trades, 76.92% positive-PnL win rate, PF 2.7385, net +12.50, DD 5.98
- 2025+ evaluation: 16 trades, 68.75% positive-PnL win rate, PF 3.4407, net +36.61, DD 3.00
- exact-M1 independent replay mismatches: 0 PnL / 0 exit / 0 reason

## Why this is not deployable

- only 16 selected evaluation trades;
- the 95% Wilson interval for 11/16 wins is approximately 44.4% to 85.8%;
- no trades occurred in 2026H1 and 2026JUL had one losing trade;
- the lead was found after a large multi-hypothesis research pass;
- it occurs around the daily session restart, where live slippage and spread behavior require prospective validation;
- evaluation AUC was only about 0.539.

## Running-system isolation

Frozen V19 and Challenger C1 were not modified, stopped, reconfigured, re-bootstrapped or used as candidate inputs.

## Authorization

Research record only. No Shadow, Discord, MT5 order, live trading, promotion or merge authorization follows from this branch.

## Required read order

1. `docs/gold_scalp_event_first_v1/GOLD_SCALP_EVENT_FIRST_V1_RESEARCH_AUDIT_20260802.md`
2. `config/gold_scalp_event_first_v1/formal_status_20260802.json`
3. `config/gold_scalp_event_first_v1/provisional_lead_contract_20260802.json`
4. `config/gold_scalp_event_first_v1/verification_20260802.json`
5. `docs/gold_scalp_event_first_v1/REPRODUCTION_NOTE_20260802.md`
