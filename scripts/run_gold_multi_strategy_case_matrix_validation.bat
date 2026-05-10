@echo off
setlocal

REM GOLD multi-strategy standard validation.
REM Safety:
REM - This BAT never passes --send directly to any MT5 sender.
REM - It runs only safe dry-run / validation BATs.
REM - Guarded demo-send validation uses a zero-payload fixture for the
REM   --allow-demo-send --send suppression case and never runs live CSV with both flags.
REM - It does not write production position_registry.csv.
REM - It does not modify existing Mochipoyo production/demo BATs.
REM - Python validators write their own outputs with Windows long-path support.
REM
REM Standard checks:
REM 1. Case Matrix 4 cases
REM    - no-signal dry-run path
REM    - sender-native registry/policy path
REM    - mock signal-present path
REM    - minute-aligned one-cycle path
REM 2. Monitor skip A/B invariance
REM    - baseline without --skip-monitor-when-no-open-signals
REM    - optimized with --skip-monitor-when-no-open-signals
REM    - confirms signal detection / intent / payload outputs are unchanged
REM 3. Same-M15 no-signal skip A/B invariance
REM    - baseline full scan
REM    - optimized warmup full scan with runtime_state creation
REM    - optimized same-M15 no-signal router skip
REM    - confirms signal detection / intent / payload outputs are unchanged while router is skipped
REM 4. Guarded demo-send safety validation
REM    - no flags suppression
REM    - --send only suppression
REM    - --allow-demo-send only suppression
REM    - zero-payload fixture suppression for --allow-demo-send --send

cd /d "%~dp0\.."

set OUT_DIR=data\research_results\gold_multi_strategy_case_matrix_validation
set MONITOR_AB_OUT_DIR=data\r\msab
set SAME_M15_AB_OUT_DIR=data\r\sm15ab
set GUARDED_DEMO_SEND_SAFETY_OUT_DIR=data\r\gdsafe

echo ============================================================
echo GOLD multi-strategy standard validation
echo NO direct --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo MONITOR_AB_OUT_DIR=%MONITOR_AB_OUT_DIR%
echo SAME_M15_AB_OUT_DIR=%SAME_M15_AB_OUT_DIR%
echo GUARDED_DEMO_SEND_SAFETY_OUT_DIR=%GUARDED_DEMO_SEND_SAFETY_OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_case_matrix_validation.py --out-dir "%OUT_DIR%"
set CASE_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD multi-strategy case matrix validation exit code: %CASE_EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_case_matrix_validation_result.json
echo case_matrix_log_csv: %OUT_DIR%\case_matrix_log.csv
echo ============================================================

if not "%CASE_EXIT_CODE%"=="0" (
  echo [ERROR] Case Matrix failed. Skipping lightweight / guarded safety validations.
  exit /b %CASE_EXIT_CODE%
)

echo ============================================================
echo GOLD multi-strategy monitor skip A/B invariance validation
echo Confirms lightweight monitor skip does not change signal detection outputs
echo NO --send / NO production registry write
echo MONITOR_AB_OUT_DIR=%MONITOR_AB_OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_monitor_skip_ab_validation.py --out-dir "%MONITOR_AB_OUT_DIR%"
set MONITOR_AB_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD monitor skip A/B validation exit code: %MONITOR_AB_EXIT_CODE%
echo summary_json: %MONITOR_AB_OUT_DIR%\latest_gold_multi_strategy_monitor_skip_ab_validation_result.json
echo ============================================================

if not "%MONITOR_AB_EXIT_CODE%"=="0" (
  echo [ERROR] Monitor skip A/B validation failed.
  exit /b %MONITOR_AB_EXIT_CODE%
)

echo ============================================================
echo GOLD multi-strategy same-M15 no-signal skip A/B invariance validation
echo Confirms same-M15 router skip does not change signal detection outputs
echo NO --send / NO production registry write
echo SAME_M15_AB_OUT_DIR=%SAME_M15_AB_OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_same_m15_skip_ab_validation.py --out-dir "%SAME_M15_AB_OUT_DIR%"
set SAME_M15_AB_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD same-M15 skip A/B validation exit code: %SAME_M15_AB_EXIT_CODE%
echo summary_json: %SAME_M15_AB_OUT_DIR%\latest_gold_multi_strategy_same_m15_skip_ab_validation_result.json
echo ============================================================

if not "%SAME_M15_AB_EXIT_CODE%"=="0" (
  echo [ERROR] Same-M15 skip A/B validation failed.
  exit /b %SAME_M15_AB_EXIT_CODE%
)

echo ============================================================
echo GOLD multi-strategy guarded demo-send safety validation
echo Confirms guarded wrapper suppresses unsafe send flag combinations
echo Case 4 uses zero-payload fixture; live CSV is NOT run with both --allow-demo-send and --send
echo NO MT5 order_send / NO production registry write
echo GUARDED_DEMO_SEND_SAFETY_OUT_DIR=%GUARDED_DEMO_SEND_SAFETY_OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_guarded_demo_send_safety_validation.py --out-dir "%GUARDED_DEMO_SEND_SAFETY_OUT_DIR%"
set GUARDED_DEMO_SEND_SAFETY_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD guarded demo-send safety validation exit code: %GUARDED_DEMO_SEND_SAFETY_EXIT_CODE%
echo summary_json: %GUARDED_DEMO_SEND_SAFETY_OUT_DIR%\latest_gold_multi_strategy_guarded_demo_send_safety_validation_result.json
echo ============================================================

if not "%GUARDED_DEMO_SEND_SAFETY_EXIT_CODE%"=="0" (
  echo [ERROR] Guarded demo-send safety validation failed.
  exit /b %GUARDED_DEMO_SEND_SAFETY_EXIT_CODE%
)

echo ============================================================
echo GOLD standard validation ALL PASS
echo Case Matrix summary: %OUT_DIR%\latest_gold_multi_strategy_case_matrix_validation_result.json
echo Monitor skip A/B summary: %MONITOR_AB_OUT_DIR%\latest_gold_multi_strategy_monitor_skip_ab_validation_result.json
echo Same-M15 skip A/B summary: %SAME_M15_AB_OUT_DIR%\latest_gold_multi_strategy_same_m15_skip_ab_validation_result.json
echo Guarded demo-send safety summary: %GUARDED_DEMO_SEND_SAFETY_OUT_DIR%\latest_gold_multi_strategy_guarded_demo_send_safety_validation_result.json
echo ============================================================

exit /b 0
