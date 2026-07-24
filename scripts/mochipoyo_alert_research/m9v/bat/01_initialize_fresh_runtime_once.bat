@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9V GOLD Fresh Multi-Timeframe Runtime Init v2 - ONE TIME ONLY
echo ============================================================
echo.
echo Keep M8C / M7C / genuine source collector RUNNING unchanged.
echo This freezes a NEW GOLD-only M9V prospective start using append-safe v2 prefix semantics.
echo It does NOT reuse or reset M7C/M8C.
echo.
echo IMPORTANT:
echo - If ChatGPT instructed recovery for the v1 prefix incident, run 00 first.
echo - Run this file only until it prints [M9V INIT PASS].
echo - After PASS, NEVER run it again and never delete/reset the new M9V v2 runtime manifest.
echo - If it prints [M9V INIT FAIL_CLOSED], no new start was frozen; send the full screen output to ChatGPT.
echo.

python "scripts\mochipoyo_alert_research\m9v\python\initialize_m9v_fresh_runtime_once_v2.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9V v2 fresh-start initialization was blocked.
  echo M8C, M7C, and collector remain unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9V v2 fresh start was frozen successfully.
echo NEXT: run 02_run_shadow_once.bat exactly once for the initial local audit.
pause
exit /b 0
