@echo off
setlocal

REM Forever minute-aligned GOLD multi-strategy Mochipoyo-loop dry-run runner.
REM Safety:
REM - This BAT never passes --send.
REM - It calls only the independent GOLD multi-strategy dry-run wrapper.
REM - It does not call existing Mochipoyo production/demo BATs.
REM - It does not write production position_registry.csv.
REM - It does not intentionally mutate existing Mochipoyo ledgers or trigger-state files.
REM - Python runner writes outputs with Windows long-path support.
REM
REM Timing:
REM - Runs every 1 minute at second 02.
REM - The strategy still evaluates the latest confirmed M15 bar.
REM - Running every minute aligns this independent dry-run loop with the existing Mochipoyo-style loop timing.
REM
REM Stop:
REM - Press Ctrl+C in this console window.

cd /d "%~dp0\.."

set OUT_DIR=data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned

echo ============================================================
echo GOLD multi-strategy Mochipoyo-loop FOREVER minute-aligned DRY-RUN runner
echo NO --send / independent wrapper only / every minute at second 02
echo OUT_DIR=%OUT_DIR%
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py ^
  --out-dir "%OUT_DIR%" ^
  --max-cycles 0 ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --no-run-immediately

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD forever minute-aligned dry-run loop exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json
echo aligned_loop_log_csv: %OUT_DIR%\aligned_loop_log.csv
echo ============================================================

exit /b %EXIT_CODE%
