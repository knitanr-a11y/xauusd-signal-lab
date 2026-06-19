@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MQL5_FILES=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
set "HIST_2025_DIR=%MQL5_FILES%\FX_OUTPUTS\mt5_candles\gold_2025"

echo Stage243 GOLD V3 SCALP rebuild audit-only
echo live_dir      = %MQL5_FILES%
echo hist_2025_dir = %HIST_2025_DIR%
echo.

python scripts\gold_v3_runtime\gold_v3_243_scalp_rebuild_no_lookahead_search_audit.py --live-dir "%MQL5_FILES%" --hist-2025-dir "%HIST_2025_DIR%"
set EXITCODE=%ERRORLEVEL%
echo.
echo Stage243 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %MQL5_FILES%\FX_OUTPUTS\gold_v3\243\paste_me.txt
endlocal
pause
exit /b %EXITCODE%
