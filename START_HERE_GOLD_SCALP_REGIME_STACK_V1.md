# START HERE — GOLD SCALP REGIME STACK V1

Date: 2026-08-02  
Branch: `feature/gold-scalp-regime-stack-v1-research`

## Formal status

`RETROSPECTIVE_REGIME_SPECIALIST_STACK_COMPLETE_NO_FORMAL_PORTFOLIO`

## Purpose

This branch records a candle-only GOLD scalping study that classified each M5 decision into a causal market regime, selected regime/side/exit specialists only from prior data at half-year boundaries, stacked the selected specialists with global one-position non-overlap, and compared the result with the same architecture without regime separation.

User boundaries remained fixed:

- standard spread 0.30 USD once;
- initial SL no greater than 5 USD;
- TP no lower than 5 USD;
- breakeven allowed;
- MT5 broker-server naive time;
- exact M1 outcome resolution;
- no V19 or Challenger C1 runtime inputs.

## Executive result

The best configuration meeting the frequency target produced 807 trades and median 20 trades/month, but WR was 39.28%, PF 0.9489 and net -95.33 USD. No formal portfolio was produced.

A two-prior-block candidate-promotion diagnostic improved PF to 1.296 and net to +56.93 USD, but produced only 80 trades and median zero trades/month.

A post-result descriptive stable core of M5 gap fill, compression release and effort/result continuation produced 226 trades, PF 1.2918 and net +160.07 USD, but it was identified after the complete walk-forward and is not formal validation.

## Read order

1. `docs/gold_scalp_regime_stack_v1/GOLD_SCALP_REGIME_STACK_V1_AUDIT_20260802.md`
2. `config/gold_scalp_regime_stack_v1/formal_status_20260802.json`
3. `config/gold_scalp_regime_stack_v1/descriptive_candidate_catalog_20260802.csv`
4. `docs/gold_scalp_regime_stack_v1/REPRODUCTION_NOTE_20260802.md`

## Prohibitions

- Do not present the descriptive three-family core as untouched validation.
- Do not delete losing blocks or interpolate thresholds to force a pass.
- Do not start Shadow, Discord or MT5 orders.
- Do not modify frozen V19 or Challenger C1.
- Do not merge this branch as a validated strategy.

## Next boundary

The next materially distinct candle-only study should estimate joint first-passage probabilities and expected times to favorable and adverse barriers, while retaining structural event direction and abstaining when the two distributions overlap.
