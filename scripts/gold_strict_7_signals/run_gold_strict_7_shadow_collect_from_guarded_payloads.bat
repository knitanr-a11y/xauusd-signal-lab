@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 shadow ledger collector
echo - collects generated strict7 guarded-demo payloads
 echo - appends them to shadow signal ledger
 echo - does NOT send MT5 orders
 echo - does NOT call AI
 echo ============================================================

python scripts\gold_strict_7_signals\append_gold_strict_7_shadow_ledger_from_guarded_payloads.py ^
  --logs-root data\runtime_logs\gold_strict_7_guarded_demo_autotrade ^
  --payload-glob **\gold_strict_7_order_payloads.csv ^
  --shadow-ledger-csv data\runtime_state\gold\strict_7\gold_strict7_shadow_signal_ledger.csv ^
  --out-root data\verification\gold_strict7_shadow_collect ^
  --max-files 500

set EXIT_CODE=%ERRORLEVEL%
echo.
echo shadow collect exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%
