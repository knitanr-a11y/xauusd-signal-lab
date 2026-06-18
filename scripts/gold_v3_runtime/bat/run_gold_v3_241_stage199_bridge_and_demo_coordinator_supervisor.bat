@echo off
setlocal
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_241_stage199_bridge_and_demo_coordinator_supervisor.py --cycles 0
set EXITCODE=%ERRORLEVEL%
echo.
echo Stage241 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\241\paste_me.txt
endlocal
pause
exit /b %EXITCODE%
