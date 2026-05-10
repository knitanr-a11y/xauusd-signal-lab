@echo off
setlocal

REM Read-only compact status viewer for GOLD multi-strategy aligned dry-run loop.
REM Safety:
REM - Does not run scanners.
REM - Does not pass --send.
REM - Does not call MT5 sender.
REM - Does not write production registry.

cd /d "%~dp0\.."

set OUT_DIR=data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned

echo ============================================================
echo GOLD multi-strategy aligned dry-run compact status
echo READ-ONLY / NO --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\show_gold_multi_strategy_aligned_dry_run_status.py --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo status viewer exit code: %EXIT_CODE%
echo ============================================================

exit /b %EXIT_CODE%
