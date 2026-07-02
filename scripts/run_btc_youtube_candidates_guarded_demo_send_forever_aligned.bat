@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set CSV_DIR=Files
set STATE_DIR=data\runtime_state\btc\youtube_candidates
set LOG_BASE=data\runtime_logs\btc

if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"

if not exist "Files\.env" (
  echo [ERROR] Files\.env is missing. DISCORD_WEBHOOK_URL must be available before starting.
  exit /b 2
)

for /f "usebackq tokens=1,* delims==" %%A in ("Files\.env") do (
  if /I "%%A"=="DISCORD_WEBHOOK_URL" set "DISCORD_WEBHOOK_URL=%%B"
)

if "%DISCORD_WEBHOOK_URL%"=="" (
  echo [ERROR] DISCORD_WEBHOOK_URL is not set in Files\.env.
  exit /b 3
)

echo ============================================================
echo BTC YouTube candidates Discord + MT5 DEMO loop
echo BTC4: 0.02 split TP1 0.01 / TP2 0.01, TP2 to BE after TP1
echo BTC5: 0.01 demo order
echo BTC6: Discord monitor only, no order
echo Demo login required: 75539039
echo Hedging account required for BTC4 split positions
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_btc_youtube_candidates_guarded_demo_send_forever_aligned.py ^
  --csv-dir "%CSV_DIR%" ^
  --log-base "%LOG_BASE%" ^
  --state-dir "%STATE_DIR%" ^
  --interval-minutes 1 ^
  --offset-seconds 10 ^
  --expected-login 75539039 ^
  --broker-symbol BTCUSD# ^
  --max-symbol-positions 6 ^
  --max-symbol-lot 0.10 ^
  --discord-webhook-env DISCORD_WEBHOOK_URL ^
  --discord-username "Mochipoyo BTC YouTube" ^
  --manager-interval-seconds 2 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%
echo BTC YouTube candidate loop exit code: %EXITCODE%
exit /b %EXITCODE%
