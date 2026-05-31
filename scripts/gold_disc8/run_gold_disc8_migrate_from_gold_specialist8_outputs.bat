@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM Migrate existing DISC8 files from gold_specialist_8 paths to gold_disc8 paths
REM ==============================================================================
REM This BAT does not call AI, MT5, or Discord.
REM It only copies already-created DISC8 definition/sample/payload files into the
REM clean data/gold_disc8 directory.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "OLD_ROOT=data\gold_specialist_8"
set "NEW_ROOT=data\gold_disc8"
set "OLD_CONFIG=%OLD_ROOT%\config"
set "NEW_CONFIG=%NEW_ROOT%\config"
set "OLD_STATIC=%OLD_ROOT%\verification\data_driven_static_rebacktest"
set "NEW_STATIC=%NEW_ROOT%\verification\data_driven_static_rebacktest"
set "OLD_AI=%OLD_ROOT%\verification\ai_review_data_driven"
set "NEW_AI=%NEW_ROOT%\verification\ai_review_data_driven"

echo ==============================================================================
echo DISC8 migrate old gold_specialist_8 outputs to gold_disc8
echo ==============================================================================
echo repo root  : %CD%
echo old root   : %OLD_ROOT%
echo new root   : %NEW_ROOT%
echo AI API     : DISABLED
echo ==============================================================================
echo.

if not exist "%NEW_CONFIG%" mkdir "%NEW_CONFIG%"
if not exist "%NEW_STATIC%" mkdir "%NEW_STATIC%"
if not exist "%NEW_AI%" mkdir "%NEW_AI%"
if not exist "%NEW_AI%\disc8_ai_review" mkdir "%NEW_AI%\disc8_ai_review"

if exist "%OLD_CONFIG%\disc8_static_rule_definitions_20260531.json" (
  copy /Y "%OLD_CONFIG%\disc8_static_rule_definitions_20260531.json" "%NEW_CONFIG%\disc8_static_rule_definitions_20260531.json" >nul
  echo [COPY] config disc8_static_rule_definitions_20260531.json
) else (
  echo [WARN] old config not found: %OLD_CONFIG%\disc8_static_rule_definitions_20260531.json
)

if exist "%OLD_STATIC%\static_rule_trade_ledger.csv" (
  copy /Y "%OLD_STATIC%\static_rule_trade_ledger.csv" "%NEW_STATIC%\static_rule_trade_ledger.csv" >nul
  echo [COPY] static_rule_trade_ledger.csv
) else (
  echo [WARN] old static_rule_trade_ledger.csv not found: %OLD_STATIC%\static_rule_trade_ledger.csv
)

for %%F in (
  latest_ai_review_sample_80_loss45.csv
  latest_ai_review_sample_80_loss45_summary_by_strategy.csv
  latest_ai_review_sample_80_loss45_monthly_distribution.csv
  latest_ai_review_sample_80_loss45_rejected.csv
  latest_ai_review_sample_80_loss45_audit_summary.json
  latest_sample_80_loss45_run_dir.txt
  latest_audit_only_console.log
  latest_disc8_payload_audit_console.log
  latest_disc8_ai_review_console.log
) do (
  if exist "%OLD_AI%\%%F" (
    copy /Y "%OLD_AI%\%%F" "%NEW_AI%\%%F" >nul
    echo [COPY] %%F
  )
)

if exist "%OLD_AI%\disc8_ai_review" (
  xcopy /E /I /Y "%OLD_AI%\disc8_ai_review" "%NEW_AI%\disc8_ai_review" >nul
  echo [COPY] disc8_ai_review folder
) else (
  echo [INFO] old disc8_ai_review folder not found yet.
)

echo.
echo New DISC8 paths:
echo   %NEW_CONFIG%
echo   %NEW_STATIC%
echo   %NEW_AI%
echo.
echo [OK] Migration copy completed. Use scripts\gold_disc8\ BAT files from now on.
echo.
pause
exit /b 0
