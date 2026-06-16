@echo off
setlocal

REM GOLD V3 Stage228 - integrated local alert-only loop runner.
REM This BAT expects the local Python file to exist:
REM scripts\gold_v3_runtime\gold_v3_228_integrated_alert_only_loop_local.py
REM
REM Keep .env and FX_OUTPUTS out of git.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_228_integrated_alert_only_loop_local.py

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage228 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\228\paste_me.txt

endlocal
pause
exit /b %EXITCODE%
