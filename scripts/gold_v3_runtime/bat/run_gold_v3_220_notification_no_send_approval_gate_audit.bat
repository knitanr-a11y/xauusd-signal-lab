@echo off
setlocal

REM GOLD V3 Stage220 - audit-only notification no-send approval gate.
REM No Discord send, no webhook, no payload activation, no MT5 order, no actual import, no live hook, no autotrade.

REM This BAT is located at scripts\gold_v3_runtime\bat.
REM Move three levels up to the repository root before invoking scripts\...
cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_220_notification_no_send_approval_gate_audit.py

set EXITCODE=%ERRORLEVEL%

echo.
if "%EXITCODE%"=="0" (
  echo Stage220 complete. Paste this file into the next chat:
  echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\220\paste_me.txt
) else (
  echo Stage220 failed with exit code %EXITCODE%.
  echo Please paste the console error into the next chat.
)

endlocal
pause
exit /b %EXITCODE%
