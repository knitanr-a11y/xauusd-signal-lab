@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 Discord preview once
echo - dry-run only
echo - no Discord send
echo - no MT5 order send
echo - no AI call
echo - no ledger append unless explicitly added
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_discord_notifier_from_csv.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --dry-run ^
  --scan-recent-bars 300 ^
  --max-notifications 10

set EXIT_CODE=%ERRORLEVEL%
echo.
echo preview exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%
