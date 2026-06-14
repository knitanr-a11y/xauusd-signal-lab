@echo off
setlocal
cd /d "%~dp0.."
python gold_v3_117n_live_valid_june_exception_feasibility.py
set EXITCODE=%ERRORLEVEL%
echo.
echo GOLD_V3_117N_EXITCODE=%EXITCODE%
echo paste_me: %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\117n\paste_me.txt
pause
exit /b %EXITCODE%
