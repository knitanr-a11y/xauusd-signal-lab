@echo off
setlocal

REM GOLD multi-strategy sender-native registry preview hook validation.
REM Safety:
REM - This BAT never passes --send.
REM - It does not write production position_registry.csv.
REM - It does not mutate existing Mochipoyo ledgers or trigger-state files.
REM - It does not modify or call run_mochipoyo_gold_demo_autotrade_forever_aligned.bat.
REM - It validates the disabled-by-default preview hook in send_mt5_order_from_payload.py.
REM - All validation outputs are written under data\r\sender_hook.

cd /d "%~dp0\.."

set BASE_OUT_DIR=data\r\sender_hook
set SENDER_OUT_DIR=%BASE_OUT_DIR%\sender
set REGISTRY_PREVIEW_CSV=%BASE_OUT_DIR%\registry_preview.csv
set REGISTRY_PREVIEW_JSON=%BASE_OUT_DIR%\registry_preview.json
set MOCK_POSITIONS_CSV=%BASE_OUT_DIR%\mp.csv
set RECONCILE_OUT_DIR=%BASE_OUT_DIR%\r
set POLICY_OUT_DIR=%BASE_OUT_DIR%\p
set PAYLOAD_CSV=data\r\ff\f\order_payloads.csv
set ORDER_LEDGER_CSV=%BASE_OUT_DIR%\dry_run_order_ledger.csv

echo ============================================================
echo GOLD sender-native registry preview hook validation
echo NO --send / NO production registry write
echo BASE_OUT_DIR=%BASE_OUT_DIR%
echo ============================================================

echo ============================================================
echo Step 1/5: run canonical full-cycle dry-run + verifier
echo This refreshes %PAYLOAD_CSV%
echo ============================================================

call scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run_with_verify.bat
set CANONICAL_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo canonical validation exit code: %CANONICAL_EXIT_CODE%
echo ============================================================

if not "%CANONICAL_EXIT_CODE%"=="0" (
  echo [ERROR] canonical validation failed. sender-native hook validation will not run.
  exit /b %CANONICAL_EXIT_CODE%
)

echo ============================================================
echo Step 2/5: run sender with disabled-by-default registry preview flags
echo payload: %PAYLOAD_CSV%
echo preview_csv: %REGISTRY_PREVIEW_CSV%
echo preview_json: %REGISTRY_PREVIEW_JSON%
echo ============================================================

python scripts\send_mt5_order_from_payload.py ^
  --input-csv "%PAYLOAD_CSV%" ^
  --order-ledger-csv "%ORDER_LEDGER_CSV%" ^
  --out-dir "%SENDER_OUT_DIR%" ^
  --symbol GOLD# ^
  --max-orders 1 ^
  --select-symbol ^
  --expected-login 75539039 ^
  --require-demo-account ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 5 ^
  --max-symbol-lot 0.05 ^
  --registry-preview-out-csv "%REGISTRY_PREVIEW_CSV%" ^
  --registry-preview-out-json "%REGISTRY_PREVIEW_JSON%"

set SENDER_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo sender-native preview exit code: %SENDER_EXIT_CODE%
echo ============================================================

if not "%SENDER_EXIT_CODE%"=="0" (
  echo [ERROR] sender-native preview failed.
  exit /b %SENDER_EXIT_CODE%
)

echo ============================================================
echo Step 3/5: build mock positions from sender-native registry preview
echo registry_csv: %REGISTRY_PREVIEW_CSV%
echo mock_positions_csv: %MOCK_POSITIONS_CSV%
echo ============================================================

python scripts\build_gold_multi_strategy_mock_positions_from_registry.py ^
  --registry-csv "%REGISTRY_PREVIEW_CSV%" ^
  --output-csv "%MOCK_POSITIONS_CSV%"

set MOCK_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo mock positions exit code: %MOCK_EXIT_CODE%
echo ============================================================

if not "%MOCK_EXIT_CODE%"=="0" (
  echo [ERROR] mock position build failed.
  exit /b %MOCK_EXIT_CODE%
)

echo ============================================================
echo Step 4/5: reconcile sender-native registry preview with mock positions
echo reconcile_out_dir: %RECONCILE_OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py ^
  --registry-csv "%REGISTRY_PREVIEW_CSV%" ^
  --positions-csv "%MOCK_POSITIONS_CSV%" ^
  --out-dir "%RECONCILE_OUT_DIR%" ^
  --symbol GOLD#

set RECONCILE_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo reconcile exit code: %RECONCILE_EXIT_CODE%
echo ============================================================

if not "%RECONCILE_EXIT_CODE%"=="0" (
  echo [ERROR] reconcile failed.
  exit /b %RECONCILE_EXIT_CODE%
)

echo ============================================================
echo Step 5/5: registry-aware policy preview using sender-native registry preview
echo policy_out_dir: %POLICY_OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py ^
  --input-csv "%PAYLOAD_CSV%" ^
  --positions-csv "%MOCK_POSITIONS_CSV%" ^
  --registry-csv "%REGISTRY_PREVIEW_CSV%" ^
  --order-ledger-csv "%ORDER_LEDGER_CSV%" ^
  --out-dir "%POLICY_OUT_DIR%" ^
  --symbol GOLD# ^
  --max-orders 1 ^
  --max-total-positions 5 ^
  --max-lot-per-order 0.02

set POLICY_EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo policy preview exit code: %POLICY_EXIT_CODE%
echo ============================================================

if not "%POLICY_EXIT_CODE%"=="0" (
  echo [ERROR] registry-aware policy preview failed.
  exit /b %POLICY_EXIT_CODE%
)

echo ============================================================
echo GOLD sender-native registry preview hook validation PASS
echo canonical_summary: data\r\ff\summary.json
echo canonical_verify_json: data\r\ff\summary_verify.json
echo sender_report: %SENDER_OUT_DIR%\mt5_order_send_report.json
echo sender_results: %SENDER_OUT_DIR%\mt5_order_send_results.csv
echo registry_preview_csv: %REGISTRY_PREVIEW_CSV%
echo registry_preview_json: %REGISTRY_PREVIEW_JSON%
echo mock_positions_csv: %MOCK_POSITIONS_CSV%
echo reconcile_json: %RECONCILE_OUT_DIR%\position_registry_reconcile_dry_run.json
echo policy_json: %POLICY_OUT_DIR%\registry_policy_preview.json
echo ============================================================

exit /b 0
