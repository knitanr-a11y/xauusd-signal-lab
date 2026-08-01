# START HERE — GOLD UNCOVERED V1

Date: 2026-08-02  
Branch: `feature/gold-uncovered-v1-research`  
Recommended separate clone: `C:\gold-uncovered-v1`

## Purpose

Discover a new GOLD candidate vector in regions not structurally targeted by the frozen V19 candidate or Challenger C1.

This is a new independent research track. It is not V20, not a V19 rescue, and not a Challenger C1 rescue.

## Absolute isolation

The following running systems remain untouched:

- `C:\gold-v19-shadow`
- `C:\gold-challenger-c1`
- `%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow`
- `%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow`

Do not stop, switch, pull, modify, rebootstrap, overwrite, rename, move, or use either running state directory.

## Prohibited research inputs

The new candidate must not read or use:

- V19 score, rank, model, wave state, episode, candidate, trade, runtime, or Discord outputs;
- Challenger C1 score, rank, wave state, episode, candidate, trade, runtime, or Discord outputs;
- V10/V17/V18/V19 outcome or signal ledgers as entry-generation inputs;
- the frozen V19 or C1 formulas as fallback, ensemble, filter, priority, or rescue logic.

Historical V19/C1 contracts may be read only to define already-covered structural regions. Their rows and outcomes are not discovery inputs.

## Already-covered structural regions

These regions are excluded from candidate generation:

1. V19 family: E40 selected direction + direction-specific P90 + causal `IMPULSE_EARLY` + first eligible event per episode.
2. Challenger C1 family: E40 selected direction + rank below P90 + causal `IMPULSE_LATE` or `CORRECTION_EARLY` + causal transition onset.

The new track must use an independently defined event kernel. It must not merely invert V19, trade every V19 rejection, or select a rank sub-band after seeing returns.

## Time and execution contract

- CSV `time` is MT5 broker-server naive bar-open time.
- The latest CSV row is closed by contract.
- Do not create open/as-of bars.
- Higher-timeframe data is usable only after its bar close time.
- Outcome execution uses exact M1.
- Same-M1 target/stop collision resolves stop first.
- No next-M1 or higher-timeframe fallback.
- No JST conversion in research logic or reports.

## Current phase

`GU1_PHASE0_SOURCE_AUTHORITY_AUDIT_PENDING`

Run only:

`00_AUDIT_SOURCES_READONLY.bat`

Phase 0 is source-only. It must not calculate labels, trades, WR, PF, PnL, DD, or candidate outcomes.

## Read order

1. `START_HERE_GOLD_UNCOVERED_V1.md`
2. `docs/gold_uncovered_v1/RESEARCH_PREREGISTRATION_20260802.md`
3. `config/gold_uncovered_v1/current_state_20260802.json`
4. `config/gold_uncovered_v1/next_action_20260802.json`
5. `config/gold_uncovered_v1/exclusion_contract_20260802.json`
6. `config/gold_uncovered_v1/discovery_contract_20260802.json`
7. `config/gold_uncovered_v1/source_reference_20260802.json`
8. `scripts/gold_uncovered_v1/source_audit.py`

## Authorization boundary

Research and audit only. No Shadow, Discord, AI judgement, MT5 order, real trading, deployment, promotion, or merge authorization follows from this track unless the user explicitly authorizes a later dedicated stage.
