@echo off
setlocal

REM GOLD V3 Stage229 - MT5 demo connection and order_check readiness.
REM This stage does NOT call order_send and does NOT place an order.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_229_mt5_demo_connection_order_check_readiness.py

set EXITCODE=%ERRORLEVEL%

echo.
if "%EXITCODE%"=="0" (
  echo Stage229 complete. Paste this file into the next chat:
  echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\229\paste_me.txt
) else (
  echo Stage229 failed with exit code %EXITCODE%.
  echo Please paste this file into the next chat if it exists:
  echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\229\paste_me.txt
)

endlocal
pause
exit /b %EXITCODE%
