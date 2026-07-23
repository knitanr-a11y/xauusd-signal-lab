@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9K BTC LONG Causal Tail-Loss State Audit - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo ============================================================
echo.

python "..\python\run_btc_long_causal_tail_loss_state_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [M9K BLOCKED]
  echo Do not repeat unchanged. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [M9K PASS]
echo Run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
