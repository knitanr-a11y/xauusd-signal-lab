@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 Discord notify forever aligned
echo - Discord send ENABLED
echo - aligned to every 5 minutes + delay
echo - duplicate prevention by ledger
echo - no MT5 order send
echo - no AI call
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_discord_notify_forever_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --send-discord ^
  --interval-minutes 5 ^
  --run-delay-seconds 20 ^
  --scan-recent-bars 36 ^
  --max-notifications 20

set EXIT_CODE=%ERRORLEVEL%
echo.
echo forever loop stopped exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%
