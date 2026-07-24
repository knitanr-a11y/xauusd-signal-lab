@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\..\.."

echo ============================================================
echo MOCHIPOYO RESEARCH - FORCED REBOOT SAFE RECOVERY
ECHO ============================================================
echo.
echo Use this ONLY after Windows/PC was forcibly restarted or powered off.
echo It checks that collector / M7C / M9V / M9Y loops are NOT running.
echo It archives and removes stale loop-lock files only.
echo It does NOT reset/delete runtime manifests, prospective starts, SQLite, M8C, M9V, or M9Y history.
echo.

python "scripts\mochipoyo_alert_research\recovery\python\recover_after_forced_reboot.py"
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
echo.
echo NEVER rerun M9V BAT00/BAT01 or M9Y BAT01 after reboot.
echo NEVER reset M7C/M8C/M9V/M9Y prospective starts.
echo.
pause
exit /b 0
