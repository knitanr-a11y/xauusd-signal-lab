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
  goto :fail
)

set "TRADE_LEDGER=data\gold_specialist_8\verification\data_driven_static_rebacktest\static_rule_trade_ledger.csv"
set "RULE_JSON=data\gold_specialist_8\config\disc8_static_rule_definitions_20260531.json"
set "OUT_ROOT=data\gold_specialist_8\verification\ai_review_data_driven\sample_80_loss45"
set "LATEST_ROOT=data\gold_specialist_8\verification\ai_review_data_driven"

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
echo ==============================================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  echo Please run this from a Python-enabled terminal or install/add Python to PATH.
  goto :fail
)

if not exist "%RULE_JSON%" (
  echo [ERROR] DISC8 rule json not found.
  echo Expected: %RULE_JSON%
  echo.
  echo Make sure you pulled the latest GitHub changes.
  goto :fail
)

if not exist "%TRADE_LEDGER%" (
  echo [ERROR] source trade ledger not found.
  echo Expected: %TRADE_LEDGER%
  echo.
  echo Required file:
  echo   static_rule_trade_ledger.csv
  echo.
  echo Put/copy it from:
  echo   gold_data_driven_static_rebacktest_20260531_outputs.zip
  echo.
  echo To:
  echo   %TRADE_LEDGER%
  echo.
  echo Creating parent folder now if missing...
  if not exist "data\gold_specialist_8\verification\data_driven_static_rebacktest" mkdir "data\gold_specialist_8\verification\data_driven_static_rebacktest"
  goto :fail
)

python scripts\gold_specialist_8\build_gold_data_driven_ai_review_sample_80_loss45.py ^
  --rule-json "%RULE_JSON%" ^
  --trade-ledger-csv "%TRADE_LEDGER%" ^
  --out-root "%OUT_ROOT%" ^
  --latest-root "%LATEST_ROOT%"

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo audit-only exit_code=%EXIT_CODE%
echo.

if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Audit-only sample build failed. Do NOT run AI review.
  goto :fail_with_code
)

echo Latest outputs:
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_summary_by_strategy.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_monthly_distribution.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_audit_summary.json
echo.
echo [OK] Audit-only sample is ready. Review the CSV/JSON before creating/running AI review BAT.
echo.
pause
exit /b 0

:fail
echo.
echo [STOP] Audit-only sample was not created.
echo.
pause
exit /b 1

:fail_with_code
echo.
echo [STOP] Audit-only sample was not created.
echo.
pause
exit /b %EXIT_CODE%
