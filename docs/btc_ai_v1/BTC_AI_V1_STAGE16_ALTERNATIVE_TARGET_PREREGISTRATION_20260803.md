# BTC AI V1 Stage 16 — Alternative Target / Direct Payoff AI Preregistration

Date: 2026-08-03  
Status: `FROZEN_BEFORE_ALTERNATIVE_TARGET_OUTCOMES`

The previous cycles showed that adding classifier types did not preserve discrimination in 2026. This cycle changes the supervised target rather than modifying failed thresholds.

## Target families

1. `NET_CLOSE_R_480`: fixed-cost directional terminal return at 480 exact M1 minutes, normalized by M15 ATR14.
2. `PATH_EDGE_R_480`: directional MFE minus 0.75 × MAE over 480 exact M1 minutes, normalized by ATR14.
3. `POLICY_PAYOFF_R_720`: realized payoff of a frozen 1 ATR stop / 2 ATR target / 720-minute maximum hold policy, including fixed 22.50 USD spread.

## AI models

- XGBoost regressor
- CatBoost regressor
- ExtraTrees regressor
- Histogram Gradient Boosting regressor
- equal-weight fold percentile-rank ensemble

Two causal feature sets, LONG/SHORT, P90/P95/P97.5 and first-cross/cooldown policies produce at most 360 raw candidates.

## Evaluation status

Development remains exactly 24 calendar months, 2024-01 through 2025-12, in four expanding folds. The historical 2026 seven-month period has already been consumed and can be used only after survivor freeze as a diagnostic. It cannot support any candidate.

All fixed cost, exact-M1, gap, monthly-frequency, development, robustness and no-rescue rules remain unchanged.
