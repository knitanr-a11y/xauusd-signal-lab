@echo off
setlocal

REM A/B validation that --skip-monitor-when-no-open-signals does not change signal detection.
REM Safety:
REM - This BAT never passes --send.
REM - It uses dedicated A/B output directories.
REM - It does not write production position_registry.csv.
REM - It does not call existing Mochipoyo production/demo BATs.

cd /d "%~dp0\.."

set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set OUT_DIR=data\research_results\gold_multi_strategy_monitor_skip_ab_validation

echo ============================================================
echo GOLD multi-strategy monitor skip A/B validation
echo baseline: no monitor skip
echo optimized: --skip-monitor-when-no-open-signals
echo NO --send / NO production registry write
echo CSV_DIR=%CSV_DIR%
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_monitor_skip_ab_validation.py ^
  --csv-dir "%CSV_DIR%" ^
  --out-dir "%OUT_DIR%" ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --fixed-lot 0.01 ^
  --magic 26050601 ^
  --max-orders 1 ^
  --deviation 50 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 5 ^
  --max-symbol-lot 0.05 ^
  --latest-confirmed-policy last ^
  --latest-confirmed-m5-policy last ^
  --latest-confirmed-m1-policy last

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD monitor skip A/B validation exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_monitor_skip_ab_validation_result.json
echo ============================================================

exit /b %EXIT_CODE%
