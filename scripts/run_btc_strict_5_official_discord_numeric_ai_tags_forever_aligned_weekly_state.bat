@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set STATE_DIR=data\runtime_state\btc\strict_5
if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"

echo ============================================================
echo BTC strict 5 OFFICIAL Discord numeric AI tags aligned runner
echo Official filter variant: buy_h4_context_conservative_v1
echo Schedule: every 1 minute at +05 seconds
echo Recommended EA InpExportSecond=2
echo Rule JSON: %STATE_DIR%\ai_tag_numeric_rules.json
echo Notification ledger: %STATE_DIR%\official_discord_numeric_ai_tag_ledger.csv
echo Python UTF-8 mode ENABLED to avoid cp932 emoji print failures
echo No MT5 call / No order_send / No OpenAI call
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.py ^
  --log-base data\runtime_logs\btc ^
  --state-dir "%STATE_DIR%" ^
  --filter-variant buy_h4_context_conservative_v1 ^
  --interval-minutes 1 ^
  --offset-seconds 5 ^
  --scan-recent-bars 5 ^
  --max-signal-age-minutes 30 ^
  --max-notifications 5 ^
  --tail-m15 3000 ^
  --tail-h1 2000 ^
  --tail-h4 1000 ^
  --send-discord

set EXITCODE=%ERRORLEVEL%
echo BTC strict 5 official Discord numeric AI tags loop exit code: %EXITCODE%
exit /b %EXITCODE%