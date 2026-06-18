@echo off
setlocal
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_243_scalp_rebuild_no_lookahead_search_audit.py
set EXITCODE=%ERRORLEVEL%
echo.
echo Stage243 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\243\paste_me.txt
endlocal
pause
exit /b %EXITCODE%
