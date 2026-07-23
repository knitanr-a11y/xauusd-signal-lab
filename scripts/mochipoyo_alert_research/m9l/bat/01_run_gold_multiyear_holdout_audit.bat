@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9L GOLD 2023-2026 Multi-Year Holdout Audit - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo Required GOLD files must remain in the MT5 Files root.
echo ============================================================
echo.

python "..\python\run_gold_multiyear_holdout_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9L was blocked.
  echo Keep M8C, M7C, and collector unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9L completed successfully.
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
