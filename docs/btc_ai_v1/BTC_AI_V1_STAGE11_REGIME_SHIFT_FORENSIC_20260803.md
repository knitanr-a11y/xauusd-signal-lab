# BTC AI V1 Stage 11 — Second-Cycle Regime Shift Forensic

Date: 2026-08-03  
Status: `COMPLETE_DIAGNOSTIC_ONLY_NO_RESCUE`

This stage explains the second-cycle failure. It does not select, modify, rescue or promote candidates.

## Direction-label base rates

| Period | Months | LONG positive | SHORT positive |
|---|---:|---:|---:|
| 2023H1 | 6 | 0.2450 | 0.2637 |
| 2023H2 | 6 | 0.2396 | 0.2378 |
| 2024H1 | 6 | 0.3526 | 0.3351 |
| 2024H2 | 6 | 0.3557 | 0.3552 |
| 2025H1 | 6 | 0.3724 | 0.3577 |
| 2025H2 | 6 | 0.3473 | 0.3681 |
| 2026_7M | 7 | 0.3324 | 0.3653 |

The aggregate SHORT label rate did not collapse in 2026; therefore the trading failure is not explained by a simple absence of downside target-before-stop events.

## Largest causal feature drift

| Feature | PSI | Standardized mean shift | Development mean | 2026 mean |
|---|---:|---:|---:|---:|
| `d1_ema20_slope4_atr` | 1.4414 | -0.4775 | +0.1243 | -0.1232 |
| `d1_trend` | 0.1949 | -0.6179 | +0.1889 | -0.3159 |
| `d1_ret4_atr` | 0.0758 | -0.2268 | +0.1430 | -0.1450 |
| `h4_ema20_slope4_atr` | 0.0588 | -0.2069 | +0.0664 | -0.0433 |
| `vol_ratio20` | 0.0438 | +0.0931 | +1.1528 | +1.2281 |
| `vol_ratio96` | 0.0372 | +0.1133 | +1.2469 | +1.3614 |
| `atr_state` | 0.0256 | -0.0016 | +1.1062 | +1.1054 |
| `break_high_96_atr` | 0.0220 | -0.1390 | -5.3237 | -5.8640 |
| `atr_ratio` | 0.0196 | -0.0002 | +0.9842 | +0.9842 |
| `h1_ema20_slope4_atr` | 0.0179 | -0.1224 | +0.0402 | -0.0229 |

The strongest shift was daily trend structure. `d1_ema20_slope4_atr` changed from +0.1243 in 2024–2025 to -0.1232 in 2026-01 through 2026-07; `d1_trend` changed from +0.1889 to -0.3159.

## Frozen-finalist score diagnostics

| Candidate | Calibration AUC | 2026 AUC | 2026 frozen events | Event label hit | 2026 baseline SHORT label | Lift |
|---|---:|---:|---:|---:|---:|---:|
| `ML2_126` | 0.5257 | 0.5088 | 492 | 0.3374 | 0.3653 | 0.9235 |
| `ML2_106` | 0.5402 | 0.5232 | 144 | 0.3819 | 0.3653 | 1.0455 |
| `ML2_127` | 0.5257 | 0.5088 | 630 | 0.3508 | 0.3653 | 0.9602 |
| `ML2_090` | 0.5252 | 0.5080 | 496 | 0.3387 | 0.3653 | 0.9271 |
| `ML2_104` | 0.5402 | 0.5232 | 285 | 0.3544 | 0.3653 | 0.9700 |

All frozen models lost discrimination: final AUC was approximately 0.508–0.523. Four of five high-score event sets had label hit rates below the unconditional 2026 SHORT-label rate. Score-level distribution PSI was small, so score magnitude appeared superficially stable while score ordering lost predictive information.

## Formal conclusion

`REGIME_AND_CONDITIONAL_RELATIONSHIP_SHIFT_MODEL_DISCRIMINATION_COLLAPSE`

- no candidate rescue;
- no threshold, side, month, feature or exit modification;
- 2026 remains consumed and diagnostic only;
- diverse AI comparisons must use rolling 2024–2025 development and require new future data for support.
