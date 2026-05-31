@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD data-driven DISC8 AI review sample 80/loss45 - AUDIT ONLY
REM ==============================================================================
REM This BAT does NOT call OpenAI.
REM This BAT does NOT send MT5 orders.
REM This BAT does NOT send Discord notifications.
REM It only builds the fixed AI-review sample CSV and audit summaries.
REM ==============================================================================

cd /d "%~dp0\..\.."
if errorlevel 1 (
  echo [ERROR] Failed to cd to repo root from: %~dp0
  echo Current directory:
  cd
  pause
  exit /b 1
)

set "TRADE_LEDGER=data\gold_specialist_8\verification\data_driven_static_rebacktest\static_rule_trade_ledger.csv"
set "RULE_JSON=data\gold_specialist_8\config\disc8_static_rule_definitions_20260531.json"
set "OUT_ROOT=data\gold_specialist_8\verification\ai_review_data_driven\sample_80_loss45"
set "LATEST_ROOT=data\gold_specialist_8\verification\ai_review_data_driven"
set "LOG_DIR=data\gold_specialist_8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_audit_only_console.log"

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
echo GOLD data-driven DISC8 AI review sample 80/loss45 - AUDIT ONLY
echo ==============================================================================
echo AI API              : DISABLED
echo MT5 order_send      : DISABLED
echo Discord send        : DISABLED
echo repo root           : %CD%
echo source trade ledger : %TRADE_LEDGER%
echo rule json           : %RULE_JSON%
echo max per strategy    : 80
echo max loss per strat  : 45
echo max non-loss/strat  : 35
echo max total           : 640
echo log file            : %LOG_FILE%
echo ==============================================================================
echo.

where python
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  echo Please run this from a Python-enabled terminal or install/add Python to PATH.
  exit /b 10
)

python --version
echo.

if not exist "%RULE_JSON%" (
  echo [ERROR] DISC8 rule json not found.
  echo Expected: %RULE_JSON%
  echo.
  echo Make sure you pulled the latest GitHub changes.
  exit /b 11
)

if not exist "%TRADE_LEDGER%" (
  echo [ERROR] source trade ledger not found.
  echo Expected: %TRADE_LEDGER%
  echo.
  echo Required file:
  echo   static_rule_trade_ledger.csv
  echo.
  echo Put/copy it from:
  echo   gold_data_driven_static_rebacktest_trade_ledger_only_20260531.zip
  echo.
  echo To:
  echo   %TRADE_LEDGER%
  echo.
  echo Creating parent folder now if missing...
  if not exist "data\gold_specialist_8\verification\data_driven_static_rebacktest" mkdir "data\gold_specialist_8\verification\data_driven_static_rebacktest"
  exit /b 12
)

echo [CHECK] Running Python import check...
python -c "import pandas as pd; print('pandas', pd.__version__)"
if errorlevel 1 (
  echo [ERROR] Python pandas import failed.
  echo Please install pandas in the Python environment used by this BAT.
  exit /b 13
)

echo.
echo [RUN] Building audit-only sample...
python scripts\gold_specialist_8\build_gold_data_driven_ai_review_sample_80_loss45.py ^
  --rule-json "%RULE_JSON%" ^
  --trade-ledger-csv "%TRADE_LEDGER%" ^
  --out-root "%OUT_ROOT%" ^
  --latest-root "%LATEST_ROOT%"

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] Audit-only sample build failed. Do NOT run AI review.
  exit /b %PY_EXIT%
)

echo Latest outputs:
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_summary_by_strategy.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_monthly_distribution.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_audit_summary.json
echo   %LATEST_ROOT%\latest_audit_only_console.log
echo.
echo [OK] Audit-only sample is ready. Review the CSV/JSON before creating/running AI review BAT.
exit /b 0
