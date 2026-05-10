@echo off
setlocal

REM GOLD multi-strategy fresh sender registry policy full-cycle dry-run + read-only verifier.
REM Safety:
REM - This BAT never passes --send.
REM - It does not write production position_registry.csv.
REM - It does not mutate existing Mochipoyo ledgers or trigger-state files.
REM - It does not modify or call run_mochipoyo_gold_demo_autotrade_forever_aligned.bat.
REM - The verifier is read-only and does not import MT5.

cd /d "%~dp0\.."

set OUT_DIR=data\r\ff
set SUMMARY_JSON=%OUT_DIR%\summary.json
set VERIFY_JSON=%OUT_DIR%\summary_verify.json
set VERIFY_CSV=%OUT_DIR%\summary_verify_checks.csv

echo ============================================================
echo GOLD multi-strategy full-cycle DRY-RUN + VERIFY
echo NO --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo ============================================================

call scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
set CYCLE_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo full-cycle dry-run exit code: %CYCLE_EXIT_CODE%
echo ============================================================

if not "%CYCLE_EXIT_CODE%"=="0" (
  echo [ERROR] full-cycle dry-run failed. verifier will not run.
  exit /b %CYCLE_EXIT_CODE%
)

echo ============================================================
echo Running read-only summary verifier
echo SUMMARY_JSON=%SUMMARY_JSON%
echo VERIFY_JSON=%VERIFY_JSON%
echo VERIFY_CSV=%VERIFY_CSV%
echo ============================================================

python scripts\verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py ^
  --summary-json "%SUMMARY_JSON%" ^
  --out-json "%VERIFY_JSON%" ^
  --out-csv "%VERIFY_CSV%"

set VERIFY_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo verifier exit code: %VERIFY_EXIT_CODE%
echo summary: %SUMMARY_JSON%
echo verify_json: %VERIFY_JSON%
echo verify_csv: %VERIFY_CSV%
echo ============================================================

exit /b %VERIFY_EXIT_CODE%
