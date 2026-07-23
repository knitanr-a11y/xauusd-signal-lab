@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9C Frozen Proxy Historical Replay - ONE TIME AUDIT
echo Tier B: PROXY_REPLAY_NOT_SOURCE_TRUTH
echo Keep M8C / M7C / collector running. Do not reset anything.
echo Context warmup fix V2: exact M1 outcomes remain valid even when early M5/H1/H4 context is unavailable.
echo ============================================================
echo.

python "..\python\run_frozen_proxy_historical_replay_v2.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9C frozen proxy historical replay was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  echo Do not repeat this BAT unchanged. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9C one-time frozen proxy historical replay completed.
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
