@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ============================================================
echo BTC strict 5 OFFICIAL Discord notifier with numeric AI tags
echo Official filter variant: buy_h4_context_conservative_v1
echo Requires: data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json
echo No MT5 call / No order_send / No OpenAI call
echo ============================================================

if not exist "data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json" (
  echo [ERROR] Missing AI tag numeric rules JSON.
  echo Run scripts\build_btc_strict_5_ai_tag_numeric_rules.bat first.
  exit /b 2
)

python scripts\btc_strict_5_signals\run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py ^
  --filter-variant buy_h4_context_conservative_v1 ^
  --ai-tag-rules-json data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json ^
  --out-dir data\runtime_logs\btc_strict_5_official_discord_numeric_ai_tags ^
  --scan-recent-bars 500 ^
  --send-discord

set EXITCODE=%ERRORLEVEL%
echo BTC strict 5 official numeric AI tag notifier exit code: %EXITCODE%
exit /b %EXITCODE%
