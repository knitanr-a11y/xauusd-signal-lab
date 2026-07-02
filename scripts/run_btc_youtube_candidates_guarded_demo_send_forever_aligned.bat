@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\.."

set "CSV_DIR=Files"
set "LEGACY_STATE_DIR=data\runtime_state\btc\youtube_candidates"

if defined LOCALAPPDATA (
  set "RUNTIME_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_youtube"
) else (
  set "RUNTIME_ROOT=%TEMP%\xauusd_signal_lab\btc_youtube"
)

set "STATE_DIR=%RUNTIME_ROOT%\state"
set "LOG_BASE=%RUNTIME_ROOT%\logs"
set "STABLE_LOG_DIR=%LOG_BASE%\youtube_candidates_operational"
set "AUDIT_DIR=%STABLE_LOG_DIR%\gold_v3_style_audit"

if not exist "%RUNTIME_ROOT%" mkdir "%RUNTIME_ROOT%"
if not exist "%STATE_DIR%" (
  mkdir "%STATE_DIR%"
  if exist "%LEGACY_STATE_DIR%" (
    echo Migrating existing runtime state to the short Windows path...
    xcopy "%LEGACY_STATE_DIR%\*" "%STATE_DIR%\" /E /I /Y >nul
  )
)
if not exist "%LOG_BASE%" mkdir "%LOG_BASE%"
if not exist "%STABLE_LOG_DIR%" mkdir "%STABLE_LOG_DIR%"
if not exist "%AUDIT_DIR%" mkdir "%AUDIT_DIR%"
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
echo BTC6: 0.01 reference-lot monitoring, no broker order
echo Demo login required: 75539039
echo Runtime root: %RUNTIME_ROOT%
echo Stable logs: %STABLE_LOG_DIR%
echo GOLD-style audit: %AUDIT_DIR%
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_btc_youtube_candidates_gold_style_audit_wrapper.py ^
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
  echo Log directory: %STABLE_LOG_DIR%
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
