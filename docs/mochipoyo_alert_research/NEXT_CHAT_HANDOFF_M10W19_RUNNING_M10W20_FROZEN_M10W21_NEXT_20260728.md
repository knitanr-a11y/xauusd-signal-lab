# MOCHIPOYO Alert Research handoff — M10W19 running / M10W20 frozen / M10W21 next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W19_RUNNING_M10W20_HYPOTHESES_FROZEN_M10W21_EVALUATION_READY_AUDIT_ONLY`

All existing forward monitors remain unchanged.

M10W19 immutable start:
`2026.07.28 02:31:00` MT5 server time.

M10W19 BAT01 is permanently forbidden. Keep only M10W19 BAT03 running. M10P/M10P2 BAT01 remain forbidden. M10V remains forbidden until both M10P and M10P2 reach 20 resolved with integrity PASS.

## Why M10W20/M10W21 exists

M10W17 found a stable LONG directional opportunity in the exact frozen bucket:

`D1_BULLISH | H4_POSITIVE | H1_MACD_POSITIVE | ATR_HIGH_GE_0P67`

Reference M10W17 metrics:
- train PF 1.22298
- validation 2025 PF 1.38415
- test 2026 PF 2.28091
- all PF 1.37235
- all +2bps PF 1.20040

M10W18 simultaneously showed that BLC1's M15 MACD-histogram zero-cross entry was weak specifically in HIGH ATR. Therefore the research question is whether entry timing, rather than the bullish direction/regime itself, caused the weakness.

The M10W17 bucket was selected after outcome screening, so M10W21 is research-exposed historical screening, not clean validation. Any passing entry still requires a brand-new fresh prospective shadow.

## M10W20 frozen hypotheses

Contract:
`config/mochipoyo_alert_research/m10w20_high_atr_bullish_entry_hypothesis_preregistration_20260728.json`

Common regime at decision:
- D1 EMA20 > EMA30 > EMA40, fully closed D1
- H4 EMA20 > EMA30, fully closed H4
- H1 TORYS MACD line(6,13,4) > 0, fully closed H1
- H1 Wilder ATR14 trailing-100 percentile >= 0.67, fully closed H1

Exactly three frozen LONG entry families:

1. `HBR1_LONG_HIGH_ATR_1H_BREAKOUT`
   - just-closed M15 close > maximum HIGH of the immediately preceding four closed M15 bars

2. `HER1_LONG_HIGH_ATR_EMA20_RECLAIM`
   - previous M15 close <= previous EMA20
   - current M15 close > current EMA20
   - current M15 EMA20 > EMA30

3. `HRC1_LONG_HIGH_ATR_RCI9_OVERSOLD_TURN`
   - previous M15 RCI9 <= -80
   - current M15 RCI9 > previous M15 RCI9

BLC1 MACD-histogram zero-cross is deliberately not reused.

After results, do NOT add variants, combine triggers, change ATR 0.67, change breakout 4-bar lookback, change EMA periods, change RCI -80, add session filters, change 240-minute horizon, or optimize exits/runners.

## M10W21 evaluation

Stage:
`M10W21_PREREGISTERED_HIGH_ATR_BULLISH_ENTRY_EVALUATION_AUDIT_ONLY`

Operator:
`scripts/mochipoyo_alert_research/m10w21/bat/01_run_preregistered_high_atr_bullish_entry_evaluation.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W21/LATEST/99_UPLOAD_PACKAGE.zip`

Evaluation:
- 2023-2024 train
- 2025 validation
- 2026 available frozen test
- actual spread
- fixed $0.20 spread sensitivity
- +1bps / +2bps extra cost
- exact M1 entry/exit
- 240-minute fixed horizon
- one-position per family
- no nearest fallback

Frozen screening tiers use the prior M10W15 standard:
- STRONG: each split PF >=1.30, all PF >=1.50, fixed0.20 all PF >=1.40, +2bps all PF >=1.20, each split >=20 and net positive
- ROBUST: each split PF >=1.10, all PF >=1.30, fixed0.20 all PF >=1.20, +2bps all PF >=1.05, each split >=20 and net positive

Any historical ROBUST/STRONG result is only eligible for a new independent fresh prospective shadow. It is not final support and must not modify M10W19 or any existing monitor.

## Next user action

Fetch/Pull latest branch while all current monitors keep running, then run only:

`scripts\mochipoyo_alert_research\m10w21\bat\01_run_preregistered_high_atr_bullish_entry_evaluation.bat`

Upload the resulting M10W21 `99_UPLOAD_PACKAGE.zip`.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- no Discord send
- no MT5 orders
- no live_ready/final_signal
- no historical backfill into existing forward
- no existing threshold/start reset
- do not rerun M10W19 BAT01
- keep M10W19 BAT03 running unchanged
