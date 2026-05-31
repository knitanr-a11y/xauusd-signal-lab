@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD specialist 8 selected_8 source build + audit ONLY - NO API
echo - source of truth: exploration CSVs only
echo - no OHLC rediscovery
echo - no OpenAI API call
echo - no MT5 order send
echo - no Discord send
echo ============================================================

python scripts\gold_specialist_8\build_gold_specialist_8_selected8_source_trades.py
set BUILD_EXIT=%ERRORLEVEL%
echo.
echo build exit_code=%BUILD_EXIT%
if not "%BUILD_EXIT%"=="0" (
  echo [STOP] build failed. See data\gold_specialist_8\verification\source_inventory\gold_specialist_8_selected8_source_inventory.json
  pause
  exit /b %BUILD_EXIT%
)

python scripts\gold_specialist_8\audit_gold_specialist_8_selected8_source_trades.py --require-all-8 --require-count-match
set AUDIT_EXIT=%ERRORLEVEL%
echo.
echo audit exit_code=%AUDIT_EXIT%
if not "%AUDIT_EXIT%"=="0" (
  echo [STOP] audit failed. Do not run AI review.
  pause
  exit /b %AUDIT_EXIT%
)

echo.
echo [OK] selected_8 source trade audit passed. AI review is still not executed by this BAT.
pause
exit /b 0
