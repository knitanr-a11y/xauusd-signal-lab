@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo GOLD V3 117N LIVE_VALID_JUNE_EXCEPTION_FEASIBILITY
echo ============================================================
echo [1/4] Working directory set
echo     %CD%
echo.
echo [2/4] Starting Python audit script
echo     python gold_v3_117n_live_valid_june_exception_feasibility.py
echo.
python gold_v3_117n_live_valid_june_exception_feasibility.py
set EXITCODE=%ERRORLEVEL%
echo.
echo [3/4] Python script finished
echo     GOLD_V3_117N_EXITCODE=%EXITCODE%
echo.
echo [4/4] Output location
echo     paste_me: %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\117n\paste_me.txt
echo ============================================================
pause
exit /b %EXITCODE%
