@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MQL5_FILES=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
set "SNAPSHOT_DIR=%MQL5_FILES%\FX_OUTPUTS\gold_v3\243\input_snapshot\latest"
set "OUTPUT_DIR=%MQL5_FILES%\FX_OUTPUTS\gold_v3\245"

echo Stage245 refined setup one-trade stack audit-only
echo snapshot_dir = %SNAPSHOT_DIR%
echo output_dir   = %OUTPUT_DIR%
echo.

python scripts\gold_v3_runtime\gold_v3_245_refined_setup_one_trade_stack_audit.py --snapshot-dir "%SNAPSHOT_DIR%" --output-dir "%OUTPUT_DIR%"
set EXITCODE=%ERRORLEVEL%
echo.
echo Stage245 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %OUTPUT_DIR%\paste_me.txt
endlocal
pause
exit /b %EXITCODE%
