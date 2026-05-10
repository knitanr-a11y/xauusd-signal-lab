@echo off
setlocal

REM Minute-aligned GOLD multi-strategy Mochipoyo-loop dry-run runner.
REM Safety:
REM - This BAT never passes --send.
REM - It calls only the independent dry-run wrapper.
REM - It does not call existing Mochipoyo production/demo BATs.
REM - It does not write production position_registry.csv.
REM - Python runner writes outputs with Windows long-path support.
REM
REM Default is ONE immediate cycle for validation safety.
REM For an intentionally infinite local dry-run loop, run the Python script directly with --max-cycles 0.
REM Default cadence is every 1 minute at second 02, matching the Mochipoyo-style loop timing.

cd /d "%~dp0\.."

set OUT_DIR=data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned

echo ============================================================
echo GOLD multi-strategy Mochipoyo-loop minute-aligned DRY-RUN runner
echo NO --send / independent wrapper only
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py ^
  --out-dir "%OUT_DIR%" ^
  --max-cycles 1 ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --run-immediately

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD minute-aligned dry-run loop exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json
echo aligned_loop_log_csv: %OUT_DIR%\aligned_loop_log.csv
echo ============================================================

exit /b %EXIT_CODE%
