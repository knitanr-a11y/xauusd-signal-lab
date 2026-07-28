M10W25B H4_S4 boundary/root-cause and causal NEITHER cohort correction — AUDIT ONLY

Run now:
  01_run_h4_s4_boundary_and_causal_neither_cohort_correction.bat

Run frequency:
  One time only for the current frozen M10W25 result.

Keep running unchanged:
  collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 / M10W19 BAT03

Never run/reset:
  M10P BAT01
  M10P2 BAT01
  M10W19 BAT01
  Any existing prospective start/runtime/history

This stage is outcome-blind. It must not read M10W24B trade ledger, PF, PnL, win/loss, +240m outcome, or future path labels.
It classifies the 21 H4_S4 historical-vs-causal mismatches and freezes the corrected 5913-row causal NEITHER pre-entry cohort only.
It does not apply MVI1/MWR1/MMO1 formulas, evaluate performance, create a fresh start, send Discord, or place MT5 orders.

Success display:
  [M10W25B PASS]

Blocked display:
  [M10W25B BLOCKED]
  Do not force a pass or tune anything. Upload the package and full screen output.

Output to upload:
  %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W25B\LATEST\99_UPLOAD_PACKAGE.zip
