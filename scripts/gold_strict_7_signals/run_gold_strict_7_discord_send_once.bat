@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 Discord send once
echo - Discord send ENABLED
echo - no MT5 order send
echo - no AI call
echo - ledger append enabled for duplicate prevention
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_discord_notifier_from_csv.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --send-discord ^
  --scan-recent-bars 300 ^
  --max-notifications 10

set EXIT_CODE=%ERRORLEVEL%
echo.
echo send exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%
