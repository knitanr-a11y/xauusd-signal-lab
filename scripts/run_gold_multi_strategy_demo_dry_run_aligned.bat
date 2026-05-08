@echo off
setlocal

REM ============================================================
REM GOLD multi-strategy demo dry-run aligned loop
REM ============================================================
REM Safety boundaries:
REM - This BAT does NOT pass --send.
REM - This BAT does NOT call the existing Mochipoyo demo autotrade BAT.
REM - This BAT does NOT modify existing Mochipoyo ledgers/trigger states.
REM - This BAT runs only the isolated multi-strategy demo dry-run loop.
REM
REM Existing Mochipoyo BAT intentionally left unchanged:
REM   scripts\run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
REM ============================================================

cd /d "%~dp0\.."

set PYTHON_EXE=C:\Users\regen\AppData\Local\Programs\Python\Python312\python.exe
set MT5_FILES_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files

set OUT_DIR=data\research_results\gold_multi_strategy_demo_dry_run_loop
set CYCLE_OUT_DIR=data\research_results\gold_multi_strategy_demo_dry_run_cycle
set ROUTER_OUT_DIR=data\research_results\gold_multi_strategy_dry_run
set BUY_OUT_DIR=data\research_results\gold_c_env_rr2_72h_live_scan
set SELL_OUT_DIR=data\research_results\gold_h1h4_bear_ab_live_loop
set ADAPTER_OUT_DIR=data\research_results\gold_multi_strategy_autotrade_adapter_dry_run
set PAYLOAD_OUT_DIR=data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run
set MT5_DRY_RUN_OUT_DIR=data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\mt5_order_check_dry_run
set ORDER_LEDGER_CSV=data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv

set BROKER_SYMBOL=GOLD#
set FIXED_LOT=0.01
set MAGIC=26050601
set EXPECTED_LOGIN=75539039
set POSITION_POLICY=block_any
set MAX_SYMBOL_POSITIONS=1
set MAX_SYMBOL_LOT=0.01
set MAX_ORDERS=1

REM ------------------------------------------------------------
REM Loop settings
REM ------------------------------------------------------------
REM ITERATIONS=0 means run forever until Ctrl+C.
REM For first manual validation, temporarily set ITERATIONS=2.
REM ------------------------------------------------------------
set ITERATIONS=0
set ALIGN_TO_SECOND=2

echo [INFO] GOLD multi-strategy demo dry-run aligned loop
echo [INFO] repo=%CD%
echo [INFO] MT5_FILES_DIR=%MT5_FILES_DIR%
echo [INFO] OUT_DIR=%OUT_DIR%
echo [INFO] BROKER_SYMBOL=%BROKER_SYMBOL%
echo [INFO] FIXED_LOT=%FIXED_LOT%
echo [INFO] EXPECTED_LOGIN=%EXPECTED_LOGIN%
echo [INFO] POSITION_POLICY=%POSITION_POLICY%
echo [INFO] MAX_SYMBOL_POSITIONS=%MAX_SYMBOL_POSITIONS%
echo [INFO] MAX_SYMBOL_LOT=%MAX_SYMBOL_LOT%
echo [INFO] SEND MODE: DISABLED. This BAT never passes --send.
echo.

"%PYTHON_EXE%" scripts\run_gold_multi_strategy_demo_dry_run_loop_aligned.py ^
  --csv-dir "%MT5_FILES_DIR%" ^
  --out-dir "%OUT_DIR%" ^
  --cycle-out-dir "%CYCLE_OUT_DIR%" ^
  --router-out-dir "%ROUTER_OUT_DIR%" ^
  --buy-out-dir "%BUY_OUT_DIR%" ^
  --sell-out-dir "%SELL_OUT_DIR%" ^
  --adapter-out-dir "%ADAPTER_OUT_DIR%" ^
  --payload-out-dir "%PAYLOAD_OUT_DIR%" ^
  --mt5-dry-run-out-dir "%MT5_DRY_RUN_OUT_DIR%" ^
  --order-ledger-csv "%ORDER_LEDGER_CSV%" ^
  --broker-symbol "%BROKER_SYMBOL%" ^
  --fixed-lot "%FIXED_LOT%" ^
  --magic "%MAGIC%" ^
  --expected-login "%EXPECTED_LOGIN%" ^
  --position-policy "%POSITION_POLICY%" ^
  --max-symbol-positions "%MAX_SYMBOL_POSITIONS%" ^
  --max-symbol-lot "%MAX_SYMBOL_LOT%" ^
  --max-orders "%MAX_ORDERS%" ^
  --iterations "%ITERATIONS%" ^
  --align-to-minute ^
  --align-to-second "%ALIGN_TO_SECOND%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo [INFO] loop exited with code %EXIT_CODE%
exit /b %EXIT_CODE%
