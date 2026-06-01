@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 build operational candidate pack - AUDIT ONLY
REM ==============================================================================
REM This BAT does NOT call OpenAI, MT5, Discord, or OHLC redetection.
REM It converts fixed group-tag-filtered source of truth into:
REM   manifest / runtime gate rules / Discord preview templates / audit JSON.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "SOT_DIR=data\gold_disc8\source_of_truth\group_tag_filtered"
set "RULE_JSON=data\gold_disc8\config\disc8_ai_group_tag_filter_rules_20260531.json"
set "OUT_DIR=data\gold_disc8\operational_candidate\group_tag_filtered"
set "LOG_DIR=data\gold_disc8\operational_candidate\group_tag_filtered"
set "LOG_FILE=%LOG_DIR%\latest_build_operational_candidate_pack_console.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

call :main > "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

type "%LOG_FILE%"
echo.
echo ==============================================================================
echo Console log saved to:
echo   %LOG_FILE%
echo exit_code=%EXIT_CODE%
echo ==============================================================================
echo.
pause
exit /b %EXIT_CODE%

:main
echo ==============================================================================
echo GOLD DISC8 build operational candidate pack - AUDIT ONLY
echo ==============================================================================
echo repo root    : %CD%
echo sot dir      : %SOT_DIR%
echo rule json    : %RULE_JSON%
echo out dir      : %OUT_DIR%
echo AI API       : DISABLED
echo MT5 send     : DISABLED
echo Discord send : DISABLED
echo OHLC detect  : DISABLED
echo ==============================================================================
echo.

where python
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  exit /b 10
)
python --version
echo.

if not exist "%SOT_DIR%\selected_disc8_group_tag_filtered_strategies.csv" (
  echo [ERROR] selected strategies source of truth not found:
  echo   %SOT_DIR%\selected_disc8_group_tag_filtered_strategies.csv
  echo Run scripts\gold_disc8\run_gold_disc8_freeze_group_tag_filtered_source_of_truth.bat first.
  exit /b 11
)

if not exist "%SOT_DIR%\group_tag_filtered_source_trade_audit.json" (
  echo [ERROR] source of truth audit not found:
  echo   %SOT_DIR%\group_tag_filtered_source_trade_audit.json
  exit /b 12
)

if not exist "%RULE_JSON%" (
  echo [ERROR] group tag rule json not found:
  echo   %RULE_JSON%
  exit /b 13
)

python scripts\gold_disc8\build_gold_disc8_operational_candidate_pack.py ^
  --sot-dir "%SOT_DIR%" ^
  --rule-json "%RULE_JSON%" ^
  --output-dir "%OUT_DIR%"

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] Operational candidate pack build failed. Do not connect to notification/live pipeline.
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %OUT_DIR%\gold_disc8_operational_strategy_manifest.csv
echo   %OUT_DIR%\gold_disc8_operational_strategy_manifest.json
echo   %OUT_DIR%\gold_disc8_runtime_group_tag_gate_rules.json
echo   %OUT_DIR%\gold_disc8_discord_notification_templates.csv
echo   %OUT_DIR%\gold_disc8_discord_notification_templates.json
echo   %OUT_DIR%\gold_disc8_discord_preview_messages.md
echo   %OUT_DIR%\gold_disc8_operational_candidate_audit.json
echo.
echo [OK] GOLD DISC8 operational candidate pack built in audit-only mode.
exit /b 0
