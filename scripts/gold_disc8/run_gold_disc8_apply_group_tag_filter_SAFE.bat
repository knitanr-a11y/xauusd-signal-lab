@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 apply group tag filter rules - SAFE profile
REM ==============================================================================
REM This BAT does NOT call OpenAI, MT5, or Discord.
REM SAFE profile blocks only risk/execution rules.
REM Positive-looking greedy rules remain watch_only.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "OUT_DIR=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\group_tag_filter_applied"
set "LOG_DIR=data\gold_disc8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_disc8_apply_group_tag_filter_SAFE_console.log"

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
echo GOLD DISC8 apply group tag filter rules - SAFE profile
echo ==============================================================================
echo repo root    : %CD%
echo output dir   : %OUT_DIR%\safe
echo AI API       : DISABLED
echo profile      : safe
echo ==============================================================================
echo.

where python
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  exit /b 10
)
python --version
echo.

python scripts\gold_disc8\apply_gold_disc8_ai_group_tag_filter_rules.py ^
  --profile safe

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] SAFE group tag filter application failed.
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %OUT_DIR%\safe\disc8_after_group_tag_filter_trade_ledger.csv
echo   %OUT_DIR%\safe\disc8_blocked_by_group_tag_filter_trade_ledger.csv
echo   %OUT_DIR%\safe\disc8_watch_only_group_tag_hits_trade_ledger.csv
echo   %OUT_DIR%\safe\disc8_after_group_tag_filter_monthly_summary.csv
echo   %OUT_DIR%\safe\disc8_after_group_tag_filter_strategy_summary.csv
echo   %OUT_DIR%\safe\disc8_group_tag_filter_rule_hit_summary.csv
echo   %OUT_DIR%\safe\disc8_group_tag_filter_audit.json
echo.
echo [OK] SAFE group tag filter applied. No OpenAI API call was made.
exit /b 0
