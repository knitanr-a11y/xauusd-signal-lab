@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\.."

set CSV_DIR=Files
set STATE_DIR=data\runtime_state\btc\youtube_candidates
set LOG_BASE=data\runtime_logs\btc
set STABLE_LOG_DIR=%LOG_BASE%\youtube_candidates_operational

if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"
if not exist "%STABLE_LOG_DIR%" mkdir "%STABLE_LOG_DIR%"
if not exist "Files" mkdir "Files"

python scripts\ensure_discord_webhook_env.py ^
  --repo-root "%CD%" ^
  --target-env "Files\.env"

if errorlevel 1 (
  echo.
  echo [ERROR] Discord Webhook configuration could not be completed.
  echo Please paste the webhook URL when prompted, then run this BAT again.
  pause
  exit /b 2
)

for /f "usebackq tokens=1,* delims==" %%A in ("Files\.env") do (
  if /I "%%A"=="DISCORD_WEBHOOK_URL" set "DISCORD_WEBHOOK_URL=%%B"
)

if not defined DISCORD_WEBHOOK_URL (
  echo [ERROR] DISCORD_WEBHOOK_URL could not be loaded from Files\.env.
  pause
  exit /b 3
)

echo ============================================================
echo BTC YouTube candidates Discord + MT5 DEMO loop
echo BTC4: 0.02 split TP1 0.01 / TP2 0.01, TP2 to BE after TP1
echo BTC5: 0.01 demo order
echo BTC6: Discord monitor only, no order
echo Demo login required: 75539039
echo Stable logs: %STABLE_LOG_DIR%
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_btc_youtube_candidates_operational_forever.py ^
  --files-dir "%CSV_DIR%" ^
  --log-base "%LOG_BASE%" ^
  --state-dir "%STATE_DIR%" ^
  --interval-minutes 1 ^
  --offset-seconds 10 ^
  --expected-login 75539039 ^
  --broker-symbol BTCUSD# ^
  --max-symbol-positions 6 ^
  --max-symbol-lot 0.10 ^
  --spread-cost-usd 30 ^
  --discord-webhook-env DISCORD_WEBHOOK_URL ^
  --discord-username "Mochipoyo BTC YouTube" ^
  --manager-interval-seconds 2 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%
echo BTC YouTube candidate loop exit code: %EXITCODE%

if not "%EXITCODE%"=="0" (
  echo.
  echo [ERROR] Runtime stopped with an error.
  echo Log directory: %CD%\%STABLE_LOG_DIR%
  if exist "%STABLE_LOG_DIR%\latest_startup_error.log" (
    echo -------- latest_startup_error.log --------
    type "%STABLE_LOG_DIR%\latest_startup_error.log"
  )
  if exist "%STABLE_LOG_DIR%\latest_cycle_error.log" (
    echo -------- latest_cycle_error.log --------
    type "%STABLE_LOG_DIR%\latest_cycle_error.log"
  )
  echo.
  pause
)

exit /b %EXITCODE%
