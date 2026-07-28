M10W25_NEITHER_PREFIX_CAUSAL_LIVE_PARITY_AUDIT_ONLY

PURPOSE
- Outcome-blind audit only.
- Prove whether the M10W24B HIGH-ATR bullish + coverage_class=NEITHER decision set can be reproduced causally at decision time.
- This stage does NOT create a fresh start and does NOT evaluate MMO1 outcomes.

RUN NOW
- 01_run_neither_prefix_causal_live_parity_audit.bat
- Run once after pulling the latest feature/mochipoyo-alert-research branch.
- Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 / M10W19 running unchanged.
- M10W19 BAT03 continues unchanged.

DO NOT RUN / DO NOT CHANGE
- Never rerun M10P BAT01.
- Never rerun M10P2 BAT01.
- Never rerun M10W19 BAT01. M10W19 restart is BAT03 only.
- Do not run M10V before both M10P and M10P2 reach >=20 resolved with integrity PASS.
- Do not change any MMO1/MVI1/MWR1 formula or threshold.
- Do not reset any prospective start/runtime/history.
- Do not backfill PC-off data.
- Do not enable Discord send, MT5 order, live_ready or final_signal.

SUCCESS / RESULT
- The BAT completes with either [M10W25 PASS] or [M10W25 MISMATCH]. Both are valid audit outcomes and produce a package.
- [M10W25 BLOCKED] means stop and send the full screen/output package if one exists. Do not force a pass.

OUTPUT
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W25\LATEST\99_UPLOAD_PACKAGE.zip

UPLOAD
- Upload only 99_UPLOAD_PACKAGE.zip from M10W25 LATEST.
- Do not start a new MMO1 shadow before this package is reviewed.
