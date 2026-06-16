@echo off
setlocal

REM GOLD V3 Stage217 - audit-only staging retention writer dry-run.
REM No Discord, no MT5 order, no actual import, no payload, no live hook, no autotrade.

cd /d "%~dp0\..\.."

python scripts\gold_v3_runtime\gold_v3_217_live_retention_writer_staging_dry_run_audit.py

echo.
echo Stage217 complete. Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\217\paste_me.txt

endlocal
pause
