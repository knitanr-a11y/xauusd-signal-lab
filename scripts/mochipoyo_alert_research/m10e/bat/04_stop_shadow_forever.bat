@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
python "scripts\mochipoyo_alert_research\m10e\python\m10e_runtime.py" stop
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [DONE] M10E stop requested. The frozen runtime/start is preserved.
) else (
  echo [STOP] M10E stop request failed. Do NOT delete runtime/locks manually.
)
pause
exit /b %RC%
