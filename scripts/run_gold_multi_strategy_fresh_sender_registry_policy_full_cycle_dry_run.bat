@echo off
setlocal

REM GOLD multi-strategy fresh sender registry policy full-cycle dry-run.
REM Safety:
REM - This BAT never passes --send.
REM - It does not write production position_registry.csv.
REM - It does not mutate existing Mochipoyo ledgers or trigger-state files.
REM - It does not modify or call run_mochipoyo_gold_demo_autotrade_forever_aligned.bat.
REM
REM Validated canonical command target:
REM fresh MT5 tick payload -> sender dry-run -> registry preview -> mock position
REM -> reconcile -> registry-aware policy preview -> same_strategy BLOCK.

cd /d "%~dp0\.."

set OUT_DIR=data\r\ff
set BROKER_SYMBOL=GOLD#
set SYMBOL=GOLD
set DIRECTION=SELL
set LOT=0.01
set SL_DISTANCE=10
set TP_DISTANCE=20
set EXPECTED_LOGIN=75539039
set MAX_SYMBOL_POSITIONS=5
set MAX_SYMBOL_LOT=0.05
set MAX_TOTAL_POSITIONS=5
set MAX_LOT_PER_ORDER=0.02

echo ============================================================
echo GOLD multi-strategy fresh sender registry policy full-cycle
echo DRY-RUN ONLY / NO --send / NO production registry write
echo OUT_DIR=%OUT_DIR%
echo ============================================================

python scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle.py ^
  --out-dir "%OUT_DIR%" ^
  --broker-symbol "%BROKER_SYMBOL%" ^
  --symbol "%SYMBOL%" ^
  --direction "%DIRECTION%" ^
  --lot "%LOT%" ^
  --sl-distance "%SL_DISTANCE%" ^
  --tp-distance "%TP_DISTANCE%" ^
  --expected-login "%EXPECTED_LOGIN%" ^
  --require-demo-account ^
  --select-symbol ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions "%MAX_SYMBOL_POSITIONS%" ^
  --max-symbol-lot "%MAX_SYMBOL_LOT%" ^
  --max-total-positions "%MAX_TOTAL_POSITIONS%" ^
  --max-lot-per-order "%MAX_LOT_PER_ORDER%"

set EXIT_CODE=%ERRORLEVEL%

echo ============================================================
echo full-cycle dry-run finished with exit code %EXIT_CODE%
echo summary: %OUT_DIR%\summary.json
echo ============================================================

exit /b %EXIT_CODE%
