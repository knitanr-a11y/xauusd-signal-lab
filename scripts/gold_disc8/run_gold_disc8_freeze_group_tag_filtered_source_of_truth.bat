@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 freeze SAFE group-tag-filtered source of truth
REM ==============================================================================
REM This BAT does NOT call OpenAI, MT5, Discord, or OHLC redetection.
REM It freezes the already-produced SAFE filtered ledger into:
REM   data\gold_disc8\source_of_truth\group_tag_filtered\
REM ==============================================================================

cd /d "%~dp0\..\.."

set "SAFE_DIR=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\group_tag_filter_applied\safe"
set "RULE_JSON=data\gold_disc8\config\disc8_ai_group_tag_filter_rules_20260531.json"
set "SOT_DIR=data\gold_disc8\source_of_truth\group_tag_filtered"
set "LOG_DIR=data\gold_disc8\source_of_truth\group_tag_filtered"
set "LOG_FILE=%LOG_DIR%\latest_freeze_group_tag_filtered_source_of_truth_console.log"

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
echo GOLD DISC8 freeze SAFE group-tag-filtered source of truth
echo ==============================================================================
echo repo root    : %CD%
echo safe dir     : %SAFE_DIR%
echo rule json    : %RULE_JSON%
echo sot dir      : %SOT_DIR%
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

if not exist "%SAFE_DIR%\disc8_after_group_tag_filter_trade_ledger.csv" (
  echo [ERROR] SAFE filtered trade ledger not found:
  echo   %SAFE_DIR%\disc8_after_group_tag_filter_trade_ledger.csv
  echo Run scripts\gold_disc8\run_gold_disc8_apply_group_tag_filter_SAFE.bat first.
  exit /b 11
)

if not exist "%SAFE_DIR%\disc8_group_tag_filter_audit.json" (
  echo [ERROR] SAFE filter audit not found:
  echo   %SAFE_DIR%\disc8_group_tag_filter_audit.json
  echo Run scripts\gold_disc8\run_gold_disc8_apply_group_tag_filter_SAFE.bat first.
  exit /b 12
)

if not exist "%RULE_JSON%" (
  echo [ERROR] group tag filter rule json not found:
  echo   %RULE_JSON%
  exit /b 13
)

python scripts\gold_disc8\freeze_gold_disc8_group_tag_filtered_source_of_truth.py ^
  --safe-dir "%SAFE_DIR%" ^
  --rule-json "%RULE_JSON%" ^
  --output-dir "%SOT_DIR%"

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] Source-of-truth freeze failed. Do not use generated outputs until fixed.
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %SOT_DIR%\selected_disc8_group_tag_filtered_strategies.csv
echo   %SOT_DIR%\group_tag_filtered_source_trade_ledger.csv
echo   %SOT_DIR%\group_tag_filtered_monthly_summary.csv
echo   %SOT_DIR%\group_tag_filtered_strategy_summary.csv
echo   %SOT_DIR%\group_tag_filtered_source_trade_audit.json
echo.
echo [OK] DISC8 group-tag-filtered source of truth frozen.
exit /b 0
