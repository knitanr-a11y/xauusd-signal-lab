# START HERE — GOLD UNCOVERED V1

Date: 2026-08-02  
Branch: `feature/gold-uncovered-v1-research`

## Current formal status

`RETROSPECTIVE_MULTI_VECTOR_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`

GU1 research was completed in the assistant execution environment. The user does not need to clone this branch or run any BAT, audit, feature, model, or backtest process on the user PC.

## Purpose and boundary

GU1 examined GOLD candidate vectors structurally separate from frozen V19 and Challenger C1. It was not V20, not a V19 rescue and not a Challenger C1 rescue.

The following running systems remained untouched:

- `C:\gold-v19-shadow`
- `C:\gold-challenger-c1`
- `%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow`
- `%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow`

GU1 candidate generation did not read or use V19 or Challenger C1 scores, ranks, wave states, episodes, runtime state, candidate rows, trades or Discord state.

## Completed vectors

1. causal H4/D1 regime transitions with first M15 confirmation;
2. tick-volume × price effort/result;
3. previous-day and multi-day reference levels;
4. raw-candle native LightGBM using causal M15/H1/H4/D1 features.

No vector produced a complete formal candidate.

The closest handcrafted lead was `EFFORT_RESULT_DIVERGENCE_REVERSAL`, but its frozen evaluation SHORT side had PF below 1.0. LONG-only rescue is prohibited.

The raw-candle ML study passed its 2024H2 calibration gate but failed from 2025H1 onward with pooled PF below 1.0 and negative net.

## Time and execution contract

- CSV `time` is MT5 broker-server naive bar-open time.
- Latest CSV rows are closed by contract.
- Higher-timeframe inputs become available only after bar close.
- Exact M1 entry and outcome evaluation are required.
- TP20 / SL10 / 480 exact contiguous M1 minutes.
- Fixed spread 0.30.
- Same-M1 target/stop collision resolves SL first.
- No fallback.

## Authoritative read order

1. `docs/gold_uncovered_v1/GOLD_UNCOVERED_V1_RESEARCH_AUDIT_20260802.md`
2. `config/gold_uncovered_v1/formal_status_20260802.json`
3. `config/gold_uncovered_v1/current_state_20260802.json`
4. `config/gold_uncovered_v1/next_action_20260802.json`
5. the preregistration contract for the individual study being audited.

## Prohibitions

- Do not delete SHORT from the volume-price lead.
- Do not retune thresholds or model probabilities.
- Do not add time, volatility, month or side filters after results.
- Do not repeat the same formulas under new names.
- Do not start a GU1 Shadow or Discord notifier.
- Do not merge the draft PR as a validated candidate.
- Do not modify V19 or Challenger C1.

## Authorization

Research and audit only. No Shadow, Discord, AI judgement, MT5 order, live trading, deployment, promotion or merge authorization follows from GU1.
