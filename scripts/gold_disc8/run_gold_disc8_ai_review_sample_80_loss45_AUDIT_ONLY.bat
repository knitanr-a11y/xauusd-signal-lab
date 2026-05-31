@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 AI review sample 80/loss45 - AUDIT ONLY
REM ==============================================================================
REM New clean DISC8 path version.
REM This BAT does NOT call OpenAI, MT5 order_send, or Discord.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "TRADE_LEDGER=data\gold_disc8\verification\data_driven_static_rebacktest\static_rule_trade_ledger.csv"
set "RULE_JSON=data\gold_disc8\config\disc8_static_rule_definitions_20260531.json"
set "OUT_ROOT=data\gold_disc8\verification\ai_review_data_driven\sample_80_loss45"
set "LATEST_ROOT=data\gold_disc8\verification\ai_review_data_driven"
set "LOG_DIR=data\gold_disc8\verification\ai_review_data_driven"
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
echo GOLD DISC8 AI review sample 80/loss45 - AUDIT ONLY
echo ==============================================================================
echo repo root           : %CD%
echo source trade ledger : %TRADE_LEDGER%
echo rule json           : %RULE_JSON%
echo latest root         : %LATEST_ROOT%
echo AI API              : DISABLED
echo ==============================================================================
echo.

where python
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  exit /b 10
)
python --version
echo.

if not exist "%RULE_JSON%" (
  echo [ERROR] DISC8 rule json not found.
  echo Expected: %RULE_JSON%
  echo Run scripts\gold_disc8\run_gold_disc8_migrate_from_gold_specialist8_outputs.bat first,
  echo or copy data\gold_specialist_8\config\disc8_static_rule_definitions_20260531.json to data\gold_disc8\config\.
  exit /b 11
)

if not exist "%TRADE_LEDGER%" (
  echo [ERROR] source trade ledger not found.
  echo Expected: %TRADE_LEDGER%
  echo Run scripts\gold_disc8\run_gold_disc8_migrate_from_gold_specialist8_outputs.bat first,
  echo or copy static_rule_trade_ledger.csv to data\gold_disc8\verification\data_driven_static_rebacktest\.
  exit /b 12
)

python -c "import pandas as pd; print('pandas', pd.__version__)"
if errorlevel 1 (
  echo [ERROR] pandas import failed.
  exit /b 13
)

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
  echo [ERROR] DISC8 sample audit failed.
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_summary_by_strategy.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_monthly_distribution.csv
echo   %LATEST_ROOT%\latest_ai_review_sample_80_loss45_audit_summary.json
echo.
echo [OK] DISC8 sample audit completed in data\gold_disc8.
exit /b 0
