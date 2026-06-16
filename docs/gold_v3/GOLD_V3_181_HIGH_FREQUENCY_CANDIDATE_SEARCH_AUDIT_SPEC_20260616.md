# GOLD V3 Stage181 High-Frequency Candidate Search Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage181 searches higher-frequency alternatives around the Stage179 selected candidate. The motivation is that the Stage179/180 base candidate is stable but may have too few trades for live monitoring and operational usefulness.

## Inputs

- Stage179 summary:
  - `MQL5/Files/FX_OUTPUTS/gold_v3/179/gold_v3_179_summary.json`
- OHLC candles using the Stage177 data-location contract:
  - 2025 historical: `Files/FX_OUTPUTS/mt5_candles/gold_2025/gold#_<tf>.csv`
  - live/continuation: `Files/goldsharp_<tf>.csv`

## Candidate source

The Stage179 selected literal rule is used as the starting point. Stage181 varies the saved literal thresholds directly, rather than rebuilding quantile condition names.

Base rule at the time of creation:

`d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`

## Search dimensions

Stage181 varies:

- saved rule thresholds near the Stage179 rule;
- TP values: 30, 35, 40, 45, 50;
- SL values: 20, 25, 30;
- horizon values: 128, base horizon, 256.

Default target full trade count is 150, and default cost is 3.0 points.

## Candidate tiers

- `A_HIGH_FREQ_STABLE`: target count met, train/test/full/recent3m/high_vol PF >= 3.0, zero negative months.
- `B_HIGH_FREQ_REVIEW`: target count met, old PF benchmark beaten, recent/high-vol checks pass, and at most one negative month.
- `C_FREQ_OK_WEAKER_RECENT_OR_VOL`: frequency and basic PF pass, but recent or volatility robustness needs manual review.
- `D_FREQ_ONLY_FAILED_ROBUSTNESS`: frequency passes but robustness fails.
- `E_TOO_FEW_TRADES`: target trade count is not met.

## Outputs

- `gold_v3_181_high_frequency_all.csv`
- `gold_v3_181_high_frequency_ranked.csv`
- `gold_v3_181_source_coverage.csv`
- `gold_v3_181_summary.json`
- `gold_v3_181_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- no source CSV mutation
- no contract mutation
- no open/as-of allowance
- no candidate pool removal
- no F002 bypass
- no live signal
- no payload
- no Discord
- no MT5 order
- no AI API
- no live hook
- no autotrade
- NO_SIGNAL Discord notification remains off

Stage181 creates review candidates only. Passing Stage181 is not live approval.
