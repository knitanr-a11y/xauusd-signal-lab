@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9D Loss Path State Feature Audit - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo ATR ratios are observation checkpoints only, not trading rules.
echo ============================================================
echo.

python "..\python\run_loss_path_state_feature_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9D loss-path state feature audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  echo Do not repeat this BAT unchanged. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9D one-time loss-path state feature audit completed.
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
