@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set OUT_DIR=data\r\btc_manual_demo_order_send_smoke_test_send_once
set BTC_AI_DISCORD_LEDGER=data\runtime_state\btc\manual_demo\btc_ai_history_discord_send_ledger.csv
set SUMMARY_JSON=%OUT_DIR%\latest_btc_manual_demo_order_send_smoke_test_send_once_ai_discord_result.json
set PREVIEW_TXT=%OUT_DIR%\ai_history_discord\btc_ai_history_discord_preview.txt
set PREVIEW_JSON=%OUT_DIR%\ai_history_discord\btc_ai_history_discord_preview.json

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
if not exist "data\runtime_state\btc\manual_demo" mkdir "data\runtime_state\btc\manual_demo"

echo ============================================================
echo BTC manual demo SEND-ONCE smoke test + AI Discord
echo This is a manual BTC smoke test, not a strategy signal.
echo Sender --send requires BOTH --allow-demo-send and --send.
echo Discord AI info is sent only after a successful guarded BTC send.
echo OUT_DIR=%OUT_DIR%
echo BTC_AI_DISCORD_LEDGER=%BTC_AI_DISCORD_LEDGER%
echo ============================================================

python scripts\run_btc_manual_demo_order_send_smoke_test_send_once_ai_discord.py ^
  --out-dir "%OUT_DIR%" ^
  --symbol BTCUSD# ^
  --direction BUY ^
  --fixed-lot 0.01 ^
  --max-symbol-lot 0.01 ^
  --max-orders 1 ^
  --min-distance-usd 100.0 ^
  --expected-login 75539039 ^
  --require-demo-account ^
  --deviation 100 ^
  --allow-demo-send ^
  --send ^
  --btc-ai-discord-send-ledger-csv "%BTC_AI_DISCORD_LEDGER%"

set EXITCODE=%ERRORLEVEL%

echo ============================================================
echo BTC manual demo send-once AI Discord exit code: %EXITCODE%
echo Summary JSON: %SUMMARY_JSON%
echo Preview TXT: %PREVIEW_TXT%
echo Preview JSON: %PREVIEW_JSON%
echo BTC AI Discord ledger: %BTC_AI_DISCORD_LEDGER%
echo ============================================================
exit /b %EXITCODE%
