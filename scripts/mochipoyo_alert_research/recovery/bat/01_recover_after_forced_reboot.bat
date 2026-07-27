@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\..\.."

echo ============================================================
echo MOCHIPOYO RESEARCH - FORCED REBOOT SAFE RECOVERY
echo ============================================================
echo.
echo Use this ONLY after Windows/PC was forcibly restarted or powered off.
echo It checks that collector / M7C / M9V / M9Y / M10B / M10E / M10P / M10P2 / M10W19 loops are NOT running.
echo It archives and removes stale loop-lock files only.
echo It does NOT reset/delete runtime manifests, prospective starts, SQLite, or forward history.
echo.

python "scripts\mochipoyo_alert_research\recovery\python\recover_after_forced_reboot_with_m10w19.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [STOP] Forced-reboot recovery was BLOCKED.
  echo Do not delete any lock/runtime manually. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo ============================================================
echo RESTART ORDER AFTER RECOVERY PASS

echo ============================================================
echo 1. Confirm MT5 / CSV export is running again.
echo 2. scripts\mochipoyo_alert_research\run_collect_events_cloudflare_forever.bat
echo 3. scripts\mochipoyo_alert_research\run_m7c_prospective_shadow_forever.bat
echo 4. scripts\mochipoyo_alert_research\m8c\bat\02_run_forward_shadow_forever.bat
echo 5. scripts\mochipoyo_alert_research\m9v\bat\03_run_shadow_forever.bat
echo 6. scripts\mochipoyo_alert_research\m9y\bat\03_run_shadow_forever.bat
echo 7. scripts\mochipoyo_alert_research\m10b\bat\03_run_shadow_forever.bat
echo 8. scripts\mochipoyo_alert_research\m10e\bat\03_run_shadow_forever.bat
echo 9. scripts\mochipoyo_alert_research\m10p\bat\03_run_shadow_forever.bat
echo 10. scripts\mochipoyo_alert_research\m10p2\bat\03_run_shadow_forever.bat
echo 11. IF M10W19 was already initialized before the reboot: scripts\mochipoyo_alert_research\m10w19\bat\03_run_shadow_forever.bat
echo.
echo NEVER rerun M9V BAT00/BAT01, M9Y BAT01, M10B BAT01, M10E BAT01, M10P BAT01, or M10P2 BAT01 after reboot.
echo AFTER M10W19 INIT PASS, NEVER rerun M10W19 BAT01; restart it with BAT03 only.
echo NEVER reset any prospective start.
echo If raw MT5 CSVs have a permanent downtime gap, that interval is unobserved and must not be backfilled from future outcomes.
echo.
pause
exit /b 0
