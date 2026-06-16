@echo off
setlocal

REM GOLD V3 Stage221 - audit-only notification text template revision.
REM No Discord send, no webhook, no payload activation, no MT5 order, no actual import, no live hook, no autotrade.

REM This BAT is located at scripts\gold_v3_runtime\bat.
REM Move three levels up to the repository root before invoking scripts\...
cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_221_notification_text_template_revision_audit.py

set EXITCODE=%ERRORLEVEL%

echo.
if "%EXITCODE%"=="0" (
  echo Stage221 complete. Paste this file into the next chat:
  echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\221\paste_me.txt
) else (
  echo Stage221 failed with exit code %EXITCODE%.
  echo Please paste the console error into the next chat.
)

endlocal
pause
exit /b %EXITCODE%
