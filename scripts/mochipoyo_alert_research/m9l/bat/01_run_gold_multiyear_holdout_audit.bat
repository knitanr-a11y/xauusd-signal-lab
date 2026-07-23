@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9L GOLD 2023-2026 Multi-Year Holdout Audit - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo Required GOLD files are read from MT5 Files\gold_v3_2023_2026\
echo ============================================================
echo.

python "..\python\run_gold_multiyear_holdout_audit_from_subfolder.py"
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
