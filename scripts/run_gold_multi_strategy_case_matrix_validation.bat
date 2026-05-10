@echo off
setlocal

REM GOLD multi-strategy case matrix validation.
REM Safety:
REM - This BAT never passes --send directly.
REM - It runs only safe dry-run / validation BATs.
REM - It does not write production position_registry.csv.
REM - It does not modify existing Mochipoyo production/demo BATs.
REM - Python validator writes its own outputs with Windows long-path support.

cd /d "%~dp0\.."

set OUT_DIR=data\research_results\gold_multi_strategy_case_matrix_validation

echo ============================================================
echo GOLD multi-strategy case matrix validation
echo NO --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_case_matrix_validation.py --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD multi-strategy case matrix validation exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_case_matrix_validation_result.json
echo case_matrix_log_csv: %OUT_DIR%\case_matrix_log.csv
echo ============================================================

exit /b %EXIT_CODE%
