@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\..\.."

set "RECOVERY=scripts\mochipoyo_alert_research\recovery\python\recover_after_forced_reboot_all_nine.py"
if not exist "%RECOVERY%" (
  echo ============================================================
  echo [STOP] ALL-NINE RECOVERY OPERATOR IS MISSING
  echo ============================================================
  echo %RECOVERY%
  echo Confirm branch feature/mochipoyo-alert-research, then Fetch/Pull again.
  echo Do not delete any lock or change any runtime/start manually.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RECOVERY%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [STOP] All-nine recovery syntax preflight failed.
  echo No lock, runtime or start was changed.
  pause
  exit /b 2
)

echo ============================================================
echo MOCHIPOYO RESEARCH - FORCED REBOOT SAFE RECOVERY
echo ALL NINE FORWARD LOOPS / PRESERVED STARTS
echo ============================================================
echo.
echo Use this ONLY after Windows/PC was forcibly restarted or powered off.
echo It checks that collector / M7C and all nine forward loops are NOT running:
echo M9V / M9Y / M10B / M10E / M10P / M10P2 / M10W19 / M10W26 / M10W34.
echo It verifies all nine immutable runtime starts before touching any lock.
echo It archives and removes stale loop-lock files only.
echo It does NOT reset/delete runtime manifests, prospective starts, state/history,
echo SQLite, bounded journals, private snapshots, or MT5 CSVs.
echo.

python "%RECOVERY%"
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
echo 1. Confirm MT5 / CSV export is running and updating again.
echo 2. scripts\mochipoyo_alert_research\run_collect_events_cloudflare_forever.bat
echo 3. scripts\mochipoyo_alert_research\run_m7c_prospective_shadow_forever.bat
echo 4. scripts\mochipoyo_alert_research\m8c\bat\02_run_forward_shadow_forever.bat
echo 5. scripts\mochipoyo_alert_research\m9v\bat\03_run_shadow_forever.bat
echo 6. scripts\mochipoyo_alert_research\m9y\bat\03_run_shadow_forever.bat
echo 7. scripts\mochipoyo_alert_research\m10b\bat\03_run_shadow_forever.bat
echo 8. scripts\mochipoyo_alert_research\m10e\bat\03_run_shadow_forever.bat
echo 9. scripts\mochipoyo_alert_research\m10p\bat\03_run_shadow_forever.bat
echo 10. scripts\mochipoyo_alert_research\m10p2\bat\03_run_shadow_forever.bat
echo 11. scripts\mochipoyo_alert_research\m10w19\bat\03_run_shadow_forever.bat
echo 12. scripts\mochipoyo_alert_research\m10w26\bat\03_run_shadow_forever.bat
echo 13. scripts\mochipoyo_alert_research\m10w34\bat\03_run_shadow_forever.bat
echo.
echo After every BAT03 window completes at least one successful cycle, run:
echo scripts\mochipoyo_alert_research\recovery\bat\06_audit_all_nine_restart_health.bat
echo.
echo NEVER rerun any initialized BAT01/initializer.
echo The one-time M10P incident recovery BAT02/BAT03 under m10p_incident are historical and must not be repeated.
echo NEVER reset any prospective start.
echo If raw MT5 CSVs have a permanent downtime gap, that interval is unobserved and must not be backfilled from future outcomes.
echo.
pause
exit /b 0
