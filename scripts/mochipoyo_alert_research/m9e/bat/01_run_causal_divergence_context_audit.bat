@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9E Causal Divergence Context Audit - ONE TIME
echo Regular + Hidden Divergence / RCI + MACD
echo Keep M8C / M7C / collector running. Do not reset anything.
echo ============================================================
echo.

python "..\python\run_causal_divergence_context_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9E causal divergence context audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  echo Do not repeat this BAT unchanged. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9E causal divergence context audit completed.
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
