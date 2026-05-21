@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set RULE_JSON=data\runtime_state\gold\strict_7\ai_tag_numeric_rules.json

echo ============================================================
echo GOLD strict 7 Discord notify forever aligned
echo - Discord send ENABLED
echo - aligned to every 1 minute + 02 seconds
echo - designed for delayed EA CSV writes
echo - reads latest confirmed CSV row: bar_offset=0
echo - lightweight candle tails
echo - duplicate prevention by ledger
echo - numeric AI tag scoring ENABLED
echo - AI tag rules: %RULE_JSON%
echo - Python UTF-8 mode ENABLED to avoid cp932 emoji print failures
echo - no MT5 order send
echo - no OpenAI call at notification time
echo ============================================================

if not exist "%RULE_JSON%" (
  echo [INFO] Missing GOLD AI tag numeric rules JSON.
  echo [INFO] Auto-building rules first...
  call scripts\build_gold_strict_7_ai_tag_numeric_rules.bat
  if errorlevel 1 (
    echo [ERROR] Failed to build GOLD AI tag numeric rules JSON.
    pause
    exit /b 2
  )
)

if not exist "%RULE_JSON%" (
  echo [ERROR] Still missing GOLD AI tag numeric rules JSON: %RULE_JSON%
  pause
  exit /b 3
)

python scripts\gold_strict_7_signals\run_gold_strict_7_discord_notify_forever_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --ai-tag-rules-json "%RULE_JSON%" ^
  --send-discord ^
  --interval-minutes 1 ^
  --run-delay-seconds 2 ^
  --scan-recent-bars 36 ^
  --bar-offset 0 ^
  --tail-m5 2000 ^
  --tail-h1 1000 ^
  --tail-h4 500 ^
  --tail-d1 300 ^
  --max-notifications 20

set EXIT_CODE=%ERRORLEVEL%
echo.
echo forever loop stopped exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%