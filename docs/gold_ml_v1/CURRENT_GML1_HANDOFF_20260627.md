# Current GML1 Handoff

Current sources:

- `docs/gold_ml_v1/META_CORE_V1_CURRENT_20260627.md`
- `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_time_causality_audit_20260627.json`
- `config/gold_ml_v1/gml1_target_gate_research_audit_v1_20260627.json`
- `config/gold_ml_v1/gml1_lifecycle_rr_research_v1_result_audit_20260627.json`
- `config/gold_ml_v1/gml1_active_core_no_ml_baseline_and_score_sizing_v1_20260627.json`

## Protected baseline

The protected baseline is Active Event Core v1 without any ML filter or sizing. Use the same four walk-forward test periods and six-hour test-start embargo as Meta Core.

- 517 one-position trades, annualized 262.63;
- LONG 339, SHORT 178;
- WR 47.39%;
- Strong +51.3954R, PF 1.1770;
- Extreme +12.8015R, PF 1.0412;
- Strong maximum drawdown 13.5675R.

Do not compare challengers with the full-history 831-event total, because that includes model-development history. Do not use the 319-trade Meta Core filtered result as the baseline.

## First positive ML synergy result

ML filtering reduced trade count and total Strong R. A different use of the same calibrated Meta Core score was therefore tested: preserve every baseline trade and use the score only for candidate-specific risk allocation.

Sizing contract:

- z-normalize the calibrated score within each candidate ID using validation only;
- size = clip(1 + k * z, 0.5, 1.5);
- normalize mean size to 1.0 so gross exposure equals the baseline;
- validation may choose k from 0, 0.15, 0.30 and 0.50;
- choose the largest validation Strong R subject to validation DD no greater than 105% of the no-ML baseline.

Selected k values: F1 0.50, F2 0.50, F3 0.50, F4 0.00.

OOS result:

- all 517 trades retained, annualized 262.63;
- Strong +63.8959R, PF 1.2246;
- Extreme +25.7754R, PF 1.0847;
- Strong maximum drawdown 13.8942R;
- Strong improved in F1, F2 and F3, and F4 was left unchanged;
- Strong +24.3% and Extreme +101.3% versus equal-size no-ML baseline at equal total exposure.

This is the first result where ML provides incremental value without replacing or shrinking the protected candidate baseline. It remains research-only and does not meet WR60/PF2.

## Hard target

A completed candidate system still requires at least 250 annualized trades and either Strong WR at least 60% or Strong PF at least 2.00. Strong and Extreme resilience, concentration and drawdown must also pass.

## Next stage

Keep the no-ML baseline and score-sizing challenger frozen. Search only for complementary candidate families that:

1. add non-overlapping proposal supply rather than replacing baseline events;
2. show candidate-specific ML lift in validation;
3. do not reduce baseline trade count or Strong R through position blocking;
4. pass rolling OOS independently before portfolio aggregation.

No model is promoted. Shadow, live, Discord and MT5 outputs remain off.
