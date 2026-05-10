@echo off
setlocal

REM GOLD multi-strategy guarded demo-send once NO-SEND entry.
REM Safety:
REM - This BAT does NOT pass --allow-demo-send.
REM - This BAT does NOT pass --send.
REM - The guarded wrapper must keep send_flag_passed_to_sender=false.
REM - Expected suppression reason: SEND_NOT_REQUESTED.
REM - Expected order_send_called_count=0 and sent_rows=0.
REM - No production position_registry.csv write.
REM - Existing Mochipoyo BATs / ledgers / trigger-state files are not modified by this BAT.

cd /d "%~dp0\.."

set OUT_DIR=data\r\gds_once_no_send

echo ============================================================
echo GOLD multi-strategy guarded demo-send once NO-SEND
echo NO --allow-demo-send / NO --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py ^
  --out-dir "%OUT_DIR%" ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --require-demo-account ^
  --fixed-lot 0.01 ^
  --magic 26050601 ^
  --max-orders 1 ^
  --deviation 50 ^
  --position-policy block_any ^
  --max-symbol-positions 1 ^
  --max-symbol-lot 0.01

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo GOLD guarded demo-send once NO-SEND exit code: %EXIT_CODE%
echo summary_json: %OUT_DIR%\latest_gold_multi_strategy_guarded_demo_send_once_result.json
echo Expected: send_flag_passed_to_sender=false / SEND_NOT_REQUESTED / order_send_called_count=0 / sent_rows=0
echo ============================================================

exit /b %EXIT_CODE%
