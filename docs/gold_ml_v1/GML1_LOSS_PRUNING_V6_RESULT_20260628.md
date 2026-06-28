# GML1 Loss Pruning V6 Result

Date: 2026-06-28  
Mode: audit-only

## Question

Can the frozen V5 candidate stream be made useful by identifying and removing losing entries before execution?

## Theoretical ceiling

If future outcomes were known and the worst actual Strong losses were removed first, pruning 40% of the V5 one-position trades would produce:

- 2025: 1,356 trades, 60.47% positive rate, Strong PF 2.259 and +656.95R;
- 2026: 436 trades, 65.37% positive rate, Strong PF 2.894 and +272.91R.

Therefore loss removal is mathematically capable of reaching the requested target. This oracle is not tradable because it uses the outcome itself.

## Causal loss models

The V6 risk layer used only information available before entry:

- frozen M1 microstructure features;
- closed M15/H1/H4/D1 context;
- time features;
- sleeve identity.

It tested LightGBM, CatBoost and linear models for:

- any negative Strong R;
- full protective loss;
- predicted Strong downside R;
- predicted Extreme downside R;
- combined risk scores.

The frozen V5 primary score remained the first gate. Risk pruning was applied second and sleeve one-position handling third.

## Loss-prediction quality

For the selected CatBoost full-loss probability model:

| Year | Rows | ROC AUC | Average precision |
|---|---:|---:|---:|
| 2024 | 1,316 | 0.469 | 0.534 |
| 2025 | 9,359 | 0.522 | 0.638 |
| 2026 | 3,642 | 0.494 | 0.585 |

An AUC near 0.50 means the model is approximately random at ranking losses above non-losses. The relationship did not generalize.

## V6 prior-year calibration

The best 2024 option was CatBoost full-loss probability with a nominal 50% prune setting.

### 2024 selection

- base: 335 trades, Strong PF 1.129, +22.99R;
- after pruning: 326 trades, Strong PF 1.179, +30.52R;
- loss R captured: 4.75%;
- winner R removed: 1.64%;
- strict gate: failed.

### 2025 unchanged replay

- base: 2,259 trades, Strong PF 0.815, -268.06R;
- after pruning: 1,609 trades, Strong PF 0.806, -200.72R;
- Extreme PF 0.730;
- loss R captured: 31.16%;
- winner R removed: 29.24%.

The filter reduced total exposure but removed almost the same fraction of profitable R as losing R, so PF became slightly worse.

### 2026 unchanged diagnostic

- base: 726 trades, Strong PF 0.954, -20.25R;
- after pruning: 718 trades, Strong PF 0.949, -22.21R;
- Extreme PF 0.908;
- loss R captured: 0.59%;
- winner R removed: 1.39%.

The prior-year calibration drifted and removed almost nothing in 2026.

## V6B causal rolling calibration

A second test ranked each risk score only against earlier candidate risk scores, without outcomes. This maintained a more consistent prune rate and separated calibration drift from prediction quality.

The 2024-selected configuration was a 2,000-candidate history and 20% prune fraction.

### 2025

- base Strong PF 0.815;
- after pruning: 1,811 trades, Strong PF 0.844, -179.54R;
- Extreme PF 0.768;
- loss R captured: 21.88%;
- winner R removed: 19.27%.

### 2026

- base Strong PF 0.954;
- after pruning: 633 trades, Strong PF 0.920, -31.01R;
- Extreme PF 0.881;
- loss R captured: 14.39%;
- winner R removed: 20.08%.

Rolling calibration improved 2025 slightly, but remained far below PF 1 and made 2026 worse. This confirms that calibration was not the main problem; the risk features do not separate losers from winners accurately enough.

## Decision

Losses can only be profitably removed when the filter captures substantially more losing R than winning R. V6 did not achieve that. The available causal features produced near-random loss ranking and the unchanged 2025 and 2026 tests failed.

The loss filter is not promoted. It may be useful only as a conservative exposure brake, not as an alpha source or as a way to rescue the current candidate stream.

The current four sleeves and live runtime remain unchanged. Live-ready, final signal, Discord, MT5 orders, automatic retraining and automatic promotion remain OFF.
