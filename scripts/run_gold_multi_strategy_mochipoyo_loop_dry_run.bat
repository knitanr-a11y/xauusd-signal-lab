@echo off
setlocal

REM Independent GOLD multi-strategy Mochipoyo-loop dry-run wrapper.
REM Safety:
REM - This BAT never passes --send.
REM - It does not call or modify the existing Mochipoyo production/demo BAT.
REM - It does not write production position_registry.csv.
REM - It does not intentionally mutate existing Mochipoyo ledgers or trigger-state files.
REM - Outputs are written under data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run.

cd /d "%~dp0\.."

set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set OUT_DIR=data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run

echo ============================================================
echo GOLD multi-strategy Mochipoyo-loop DRY-RUN wrapper
echo NO --send / NO existing Mochipoyo BAT mutation
echo CSV_DIR=%CSV_DIR%
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run.py ^
  --csv-dir "%CSV_DIR%" ^
  --out-dir "%OUT_DIR%" ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --require-demo-account ^
  --select-symbol ^
  --fixed-lot 0.01 ^
  --magic 26050601 ^
  --max-orders 1 ^
  --deviation 50 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 5 ^
  --max-symbol-lot 0.05

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD multi-strategy Mochipoyo-loop dry-run exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json
echo cycle_log_csv: %OUT_DIR%\gold_multi_strategy_mochipoyo_loop_dry_run_log.csv
echo ============================================================

exit /b %EXIT_CODE%
