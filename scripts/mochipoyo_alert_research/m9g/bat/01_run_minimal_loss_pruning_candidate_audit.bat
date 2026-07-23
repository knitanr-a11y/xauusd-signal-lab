@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9G Minimal Loss Pruning Candidate Audit - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo SAME-SAMPLE hypothesis assessment only; no live gate promotion.
echo ============================================================
echo.

python "..\python\run_minimal_loss_pruning_candidate_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9G minimal loss pruning candidate audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  echo Do not repeat this BAT unchanged. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9G one-time candidate audit completed.
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
