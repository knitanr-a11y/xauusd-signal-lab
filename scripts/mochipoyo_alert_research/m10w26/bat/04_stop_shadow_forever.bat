@echo off
setlocal EnableExtensions EnableDelayedExpansion

if "%LOCALAPPDATA%"=="" (
  echo [M10W26 STOP BLOCKED] LOCALAPPDATA unavailable.
  pause
  exit /b 2
)
set "RUNTIME=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\m10w26_runtime"
set "LOCK=%RUNTIME%\m10w26_shadow_loop.lock"
set "STOP=%RUNTIME%\STOP_M10W26_SHADOW_LOOP"

if not exist "%RUNTIME%" (
  echo [M10W26 STOP] Runtime directory does not exist. Nothing was changed.
  pause
  exit /b 0
)
if not exist "%LOCK%" (
  echo [M10W26 STOP] Loop lock is absent. M10W26 is already stopped.
  pause
  exit /b 0
)

>"%STOP%" echo NORMAL_M10W26_STOP_REQUEST
echo [M10W26 STOP REQUESTED] Waiting for the runner to remove its own lock...
set /a WAITED=0

:wait
if not exist "%LOCK%" goto :pass
if !WAITED! GEQ 180 goto :timeout
timeout /t 1 /nobreak >nul
set /a WAITED+=1
goto :wait

:pass
if exist "%STOP%" (
  echo [M10W26 STOP REVIEW] Lock disappeared but STOP file remains. Do not delete it manually.
  echo Send this screen to ChatGPT.
  pause
  exit /b 3
)
echo [M10W26 STOP PASS] Runner stopped naturally and removed its own lock.
echo Runtime and immutable start remain preserved. Restart only with BAT03.
pause
exit /b 0

:timeout
echo [M10W26 STOP BLOCKED] Lock remains after 180 seconds.
echo Do not taskkill the process or delete the lock. Send this screen to ChatGPT.
pause
exit /b 3
