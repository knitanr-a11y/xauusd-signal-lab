@echo off
setlocal

REM GOLD minimal live notification launcher
REM - Runs the validated Python loop
REM - Sends Discord notifications only for NEW live-window rows
REM - Does NOT perform auto-trading
REM - Stops on error
REM - Press Ctrl+C to stop manually

cd /d "%~dp0"

echo ========================================
echo GOLD minimal live notification loop
echo Discord send: ENABLED
echo Auto trade: DISABLED
echo Out dir: data\ml_live_run_current
echo ========================================
echo.

python scripts\run_mochipoyo_gold_minimal_live_loop_dry.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --out-dir data\ml_live_run_current ^
  --symbol GOLD ^
  --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv ^
  --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv ^
  --forever ^
  --sleep-seconds 15 ^
  --commit-trigger-state ^
  --commit-ledger ^
  --discord-send ^
  --discord-max-rows 5 ^
  --discord-style compact ^
  --stop-on-error

set EXITCODE=%ERRORLEVEL%
echo.
echo ========================================
echo Loop stopped. Exit code: %EXITCODE%
echo Summary CSV:
echo data\ml_live_run_current\gold_minimal_live_loop_live_summary.csv
echo ========================================
echo.
pause
exit /b %EXITCODE%
