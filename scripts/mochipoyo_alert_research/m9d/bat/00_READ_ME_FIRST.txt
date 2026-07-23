M9D LOSS PATH STATE FEATURE AUDIT

Purpose
- Keep M8C, M7C, and collector running unchanged.
- Use the reviewed M9C Tier-B exact-M1 population to inspect what the market looks like DURING adverse movement.
- ATR ratios are observation checkpoints only. They are NOT entry filters, stop levels, or promoted trading rules.
- At each checkpoint M9D records only features from bars already closed at that decision time.
- Future returns/MFE/MAE are labels only after the checkpoint has been fixed.

1) 01_run_loss_path_state_feature_audit.bat
- Run ONE TIME after M9C PASS has been reviewed.
- May run simultaneously with M8C / M7C / collector.
- Success: [M9D PASS]
- Blocked: [M9D BLOCKED]
- If blocked, do not repeat unchanged. Keep the full screen output.

2) 02_open_latest_results.bat
- Opens:
  %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9D\LATEST
- Submit only:
  99_UPLOAD_PACKAGE.zip

Safety
- audit-only
- no Discord send
- no MT5 order
- no live-ready/final-signal promotion
- no M7C formula/threshold change
- no M8C prospective reset
