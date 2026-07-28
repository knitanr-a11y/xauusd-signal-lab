@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "RUNTIME_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\m10w34_runtime"
set "STOP_FILE=%RUNTIME_ROOT%\STOP_M10W34_SHADOW_LOOP"
if not exist "%RUNTIME_ROOT%" (
  echo [M10W34 STOP] Runtime folder does not exist. Nothing was changed.
  pause
  exit /b 2
)
>"%STOP_FILE%" echo requested
if errorlevel 1 (
  echo [M10W34 STOP BLOCKED] Could not create STOP file. Do not taskkill or delete locks.
  pause
  exit /b 2
)
echo [M10W34 STOP REQUESTED] The runner will exit naturally and remove its own lock.
echo Do not delete the lock or close the runner forcibly.
pause
exit /b 0
