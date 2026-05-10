@echo off
setlocal

REM GOLD multi-strategy mock signal-present path validation.
REM Safety:
REM - This BAT never passes --send.
REM - It creates a mock router OPEN_POSITION intent and validates downstream dry-run path.
REM - It does not call existing Mochipoyo production/demo BATs.
REM - It does not write production position_registry.csv.
REM - It uses Windows long-path support in the Python validator.

cd /d "%~dp0\.."

set OUT_DIR=data\research_results\gold_multi_strategy_mock_signal_path_validation

echo ============================================================
echo GOLD multi-strategy mock signal-present path validation
echo NO --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_mock_signal_path_validation.py ^
  --out-dir "%OUT_DIR%" ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --require-demo-account ^
  --select-symbol ^
  --direction SELL ^
  --lot 0.01 ^
  --sl-usd 10.0 ^
  --tp-usd 20.0 ^
  --magic 26050601 ^
  --max-orders 1 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 5 ^
  --max-symbol-lot 0.05 ^
  --deviation 50

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD mock signal path validation exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_mock_signal_path_validation_result.json
echo ============================================================

exit /b %EXIT_CODE%
