@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M9Y GOLD Payoff Fresh Prospective Shadow - ONE SHOT AUDIT
echo ============================================================
echo Keep M8C / M7C / collector / M9V RUNNING unchanged.
echo Run after M9Y 01 has PASSed. Do not run together with M9Y 03 forever loop.
echo.
python "scripts\mochipoyo_alert_research\m9y\python\run_m9y_shadow_once.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
 echo.
 echo [STOP] M9Y one-shot blocked. M9V and all existing monitors remain unchanged.
 echo Send the full screen output to ChatGPT.
 pause
 exit /b %RC%
)
echo.
echo [DONE] M9Y one-shot completed. Run 05_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip before starting 03.
pause
exit /b 0
