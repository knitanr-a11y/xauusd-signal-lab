@echo off
setlocal

REM GOLD V3 Stage227 - alert-only runtime queue binding audit.
REM No network call and no order action.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_227_alert_only_runtime_queue_binding_audit.py

set EXITCODE=%ERRORLEVEL%

echo.
if "%EXITCODE%"=="0" (
  echo Stage227 complete. Paste this file into the next chat:
  echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\227\paste_me.txt
) else (
  echo Stage227 failed with exit code %EXITCODE%.
  echo Please paste the console error into the next chat.
)

endlocal
pause
exit /b %EXITCODE%
