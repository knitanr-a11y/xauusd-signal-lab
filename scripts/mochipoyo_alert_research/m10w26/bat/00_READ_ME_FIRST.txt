M10W26 MMO1 causal-NEITHER fresh prospective shadow V2 — AUDIT ONLY

Keep collector, M7C, M8C, M9V, M9Y, M10B, M10E, M10P, M10P2 and M10W19 running unchanged.

Order for the first launch only:
1. Fetch/Pull feature/mochipoyo-alert-research.
2. Run 01_initialize_fresh_start_once.bat exactly once.
   - Before writing a start, V2 audits all six frozen M10W25 causal coverage families on a verified private snapshot.
   - A new M10W26-only immutable MT5-server-time start is created only after that audit passes.
3. After both PRESTART ENGINE PASS and INIT PASS, run 03_run_shadow_forever.bat and keep its window open.
4. Wait for the first [M10W26 PASS] cycle.
5. While M10W26 remains running, run 05_audit_initial_health.bat.
6. Upload only:
   %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W26_INITIAL_HEALTH\LATEST\99_UPLOAD_PACKAGE.zip
7. Use 04_stop_shadow_forever.bat only for a normal requested stop.
8. After initialization, never rerun BAT01. Restart only with BAT03.

02_run_shadow_once.bat is a read/rebuild audit helper and is not the persistent operator.

M10W26 is independent from all existing runtimes and starts. It does not send Discord messages, place MT5 orders, enable a live gate, modify M10W19, or backfill pre-start candidates.

Never delete or edit the M10W26 runtime manifest, state, prestart audit, lock, STOP file, private snapshot or adapter journal manually.
Never taskkill M10W26. If BAT01, BAT03 or BAT05 reports BLOCKED/REVIEW, preserve the full screen and all files and send them to ChatGPT.
