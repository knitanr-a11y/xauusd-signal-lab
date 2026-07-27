# MOCHIPOYO Alert Research handoff — M10W14 PASS / M10W15 frozen / M10W16 next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current state

`M10W14_PASS_M10W15_HYPOTHESES_FROZEN_M10W16_EVALUATION_READY_AUDIT_ONLY`

All existing forward monitors continue unchanged. No existing start or threshold is modified. M10P/M10P2 BAT01 remain forbidden. M10V remains forbidden until both existing SHORT families reach 20 resolved with integrity PASS.

## M10W14 result

Uploaded package SHA256:
`bab606b95fee01ee9b7437a5e66e91d6b5529353961713243afbbdb8d3b8b1ef`

M15 eligible windows: 81,329
- LONG_ONLY 2,749
- SHORT_ONLY 4,378
- BOTH 177
- NEITHER 74,025

Important caveat: NEITHER means no candidate event timestamp in that M15 window; it is not missed-profit evidence and not a holding-period coverage measure.

Structural finding:
- combined SHORT presence windows = 4,555
- 98.99% have H4 EMA20-EMA30 positive
- 98.81% are H1 high-ATR tercile
- 89.79% are D1 bullish stack

Primary blind spot:
`D1 EMA20<EMA30<EMA40 AND H4 EMA20<EMA30 AND H1 MACD line<0`
- 5,146 M15 windows
- SHORT presence only 19 (0.369%)
- NEITHER 5,090 (98.91%)

This is structural coverage evidence only, not edge evidence.

## M10W15 preregistration

Frozen before outcome evaluation:
`config/mochipoyo_alert_research/m10w15_blind_spot_trend_continuation_hypothesis_preregistration_20260728.json`

Exactly two symmetric hypotheses:

1. `BSC1_SHORT_BEAR_TREND_PULLBACK_ZERO_CROSS`
   - closed D1 EMA20<30<40
   - closed H4 EMA20<EMA30
   - closed H1 TORYS MACD line < 0
   - closed M15 MACD histogram crosses >0 to <=0
   - decision / exact entry = next M15 open

2. `BLC1_LONG_BULL_TREND_PULLBACK_ZERO_CROSS`
   - exact symmetric opposite
   - D1 EMA20>30>40
   - H4 EMA20>EMA30
   - H1 MACD line >0
   - M15 histogram crosses <0 to >=0

No ATR entry filter. No threshold tuning. Fixed horizon 240m. Exact M1 execution. One-position per family.

## M10W16

Operator:
`scripts/mochipoyo_alert_research/m10w16/bat/01_run_preregistered_blind_spot_trend_continuation_evaluation.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W16/LATEST/99_UPLOAD_PACKAGE.zip`

Evaluation is frozen:
- train 2023-2024
- validation 2025
- test 2026 available frozen history
- actual spread
- fixed $0.20 sensitivity
- +1/+2 bps extra-cost sensitivity
- count / WR / PF / net / payoff / DD / losing streak

Predeclared tiers are in M10W15. Do not change them after results.

Only ROBUST_CANDIDATE or STRONG_CANDIDATE may advance to a new independent fresh prospective shadow. Historical support alone is not final support. A failed family must not be threshold-rescued from its M10W16 outcomes.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- no existing forward modification
- no historical backfill into existing forward
- no existing threshold/start reset
- no Discord / MT5 orders / live_ready / final_signal
