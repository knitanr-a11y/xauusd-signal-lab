@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set RULE_JSON=data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json

echo ============================================================
echo BTC strict 5 OFFICIAL Discord notifier with numeric AI tags
echo Official filter variant: buy_h4_context_conservative_v1
echo AI tag rules: %RULE_JSON%
echo No MT5 call / No order_send / No OpenAI call
echo ============================================================

if not exist "%RULE_JSON%" (
  echo [INFO] Missing AI tag numeric rules JSON.
  echo [INFO] Auto-building rules first...
  call scripts\build_btc_strict_5_ai_tag_numeric_rules.bat
  if errorlevel 1 (
    echo [ERROR] Failed to build AI tag numeric rules JSON.
    exit /b 2
  )
)

if not exist "%RULE_JSON%" (
  echo [ERROR] Still missing AI tag numeric rules JSON: %RULE_JSON%
  exit /b 3
)

python scripts\btc_strict_5_signals\run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py ^
  --filter-variant buy_h4_context_conservative_v1 ^
  --ai-tag-rules-json "%RULE_JSON%" ^
  --out-dir data\runtime_logs\btc_strict_5_official_discord_numeric_ai_tags ^
  --scan-recent-bars 500 ^
  --max-signal-age-minutes 30 ^
  --send-discord

set EXITCODE=%ERRORLEVEL%
echo BTC strict 5 official numeric AI tag notifier exit code: %EXITCODE%
exit /b %EXITCODE%
