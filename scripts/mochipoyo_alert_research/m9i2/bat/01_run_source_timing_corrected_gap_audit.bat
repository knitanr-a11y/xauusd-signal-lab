@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9I2 Source Timing Corrected Gap Audit - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo Corrects source decision/execution from source bar open to next M15 open.
echo ============================================================
echo.

python "..\python\run_source_timing_corrected_gap_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9I2 timing-corrected audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  echo Do not repeat this BAT unchanged. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9I2 timing-corrected audit completed.
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
