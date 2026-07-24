@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10H PRIMARY_SHORT Source Fidelity Audit
echo AUDIT ONLY - READ EXISTING M7C PROSPECTIVE EVIDENCE ONLY
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo This does NOT refit M7C and does NOT use trade outcomes.
echo.
python "scripts\mochipoyo_alert_research\m10h\python\run_primary_short_source_fidelity_audit.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10H was BLOCKED.
  echo Do NOT reset or reinitialize any running monitor.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo [DONE] M10H PASS.
echo NEXT: run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
