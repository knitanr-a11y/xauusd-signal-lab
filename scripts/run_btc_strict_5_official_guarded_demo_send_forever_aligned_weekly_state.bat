@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set STATE_DIR=data\runtime_state\btc\strict_5
if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"

echo ============================================================
echo BTC strict 5 OFFICIAL guarded demo-send aligned runner
echo Official filter variant: buy_h4_context_conservative_v1
echo Schedule: every 1 minute at +02 seconds
echo Persistent order ledger: %STATE_DIR%\official_guarded_demo_order_ledger.csv
echo D1 is not used by BTC strict 5
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state.py ^
  --log-base data\runtime_logs\btc ^
  --state-dir "%STATE_DIR%" ^
  --filter-variant buy_h4_context_conservative_v1 ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --scan-recent-bars 5 ^
  --max-signal-age-minutes 30 ^
  --tail-m15 3000 ^
  --tail-h1 2000 ^
  --tail-h4 1000 ^
  --position-policy block_any ^
  --max-symbol-positions 1 ^
  --max-symbol-lot 0.01 ^
  --max-orders 1 ^
  --lot 0.01 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%
echo BTC strict 5 official runner exit code: %EXITCODE%
exit /b %EXITCODE%
