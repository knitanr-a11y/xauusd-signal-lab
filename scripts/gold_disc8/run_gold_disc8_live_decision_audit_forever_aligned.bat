@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set MANIFEST_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_operational_strategy_manifest.json
set GATE_RULES_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_runtime_group_tag_gate_rules.json

echo ============================================================
echo GOLD DISC8 SAFE live decision audit forever aligned
echo - COMMON decision ledger only
echo - Discord send DISABLED
echo - MT5 order_send DISABLED
echo - OpenAI call DISABLED
echo - aligned to every 1 minute + 05 seconds
echo - reads latest CONFIRMED CSV row: bar_offset=1
echo - runtime group-tag gate rules loaded for audit only
echo - without validated pre-send tagger, decisions are PENDING_TAGGER
echo - dispatch_ready is FORCE-FALSE in safe wrapper
echo - live decision ledger is append-only with decision_key de-duplication
echo - audit freshness window: 60 minutes for M15 diagnosis only
echo - Python UTF-8 mode ENABLED to avoid cp932 print failures
echo ============================================================

if not exist "%MANIFEST_JSON%" (
  echo [ERROR] Missing DISC8 operational manifest JSON:
  echo   %MANIFEST_JSON%
  echo Run scripts\gold_disc8\run_gold_disc8_build_operational_candidate_pack_AUDIT_ONLY.bat first.
  pause
  exit /b 2
)

if not exist "%GATE_RULES_JSON%" (
  echo [ERROR] Missing DISC8 runtime gate rules JSON:
  echo   %GATE_RULES_JSON%
  echo Run scripts\gold_disc8\run_gold_disc8_build_operational_candidate_pack_AUDIT_ONLY.bat first.
  pause
  exit /b 3
)

python scripts\gold_disc8\run_gold_disc8_live_decision_audit_forever_safe.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --manifest-json "%MANIFEST_JSON%" ^
  --gate-rules-json "%GATE_RULES_JSON%" ^
  --out-dir "data/runtime_logs/gold_disc8_live_decision_audit" ^
  --interval-minutes 1 ^
  --run-delay-seconds 5 ^
  --scan-recent-bars 36 ^
  --bar-offset 1 ^
  --max-signal-age-minutes 60 ^
  --mt5-to-local-hours 6 ^
  --tail-m15 3000 ^
  --tail-h1 1500 ^
  --tail-h4 800 ^
  --tail-d1 500 ^
  --max-decisions 50

set EXIT_CODE=%ERRORLEVEL%
echo.
echo GOLD DISC8 SAFE live decision audit forever loop stopped exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%
