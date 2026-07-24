@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10D\LATEST"

if not exist "%ROOT%" (
  echo [M10D BLOCKED] LATEST output not found:
  echo %ROOT%
  echo Run 01_run_h1_compound_loss_filter_reproduction.bat first.
  pause
  exit /b 2
)

echo Opening M10D latest results:
echo %ROOT%
start "" explorer "%ROOT%"

echo.
echo Upload only 99_UPLOAD_PACKAGE.zip to ChatGPT for review.
echo Do NOT start any new prospective filter monitor until the package is reviewed.
pause
exit /b 0
