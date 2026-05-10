@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyy"') do set LOG_YEAR=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format MM"') do set LOG_MONTH=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=Get-Date; $c=[Globalization.CultureInfo]::InvariantCulture; $w=$c.Calendar.GetWeekOfYear($d,[Globalization.CalendarWeekRule]::FirstFourDayWeek,[DayOfWeek]::Monday); 'week_{0:D2}' -f $w"') do set LOG_WEEK=%%I

set LOG_ROOT=data\runtime_logs\gold\%LOG_YEAR%\%LOG_MONTH%\%LOG_WEEK%\multi_strategy_gold
set OUT_DIR=%LOG_ROOT%\loop

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo ============================================================
echo GOLD multi-strategy GUARDED DEMO SEND FOREVER aligned runner
echo Weekly log layout / independent sidecar
echo Existing Mochipoyo GOLD BAT is not modified
echo LOG_ROOT=%LOG_ROOT%
echo OUT_DIR=%OUT_DIR%
echo Sender --send requires BOTH --allow-demo-send and --send
echo Position policy: allow_any_until_max / duplicate guard: order_key ledger
echo Adapter lot: BUY=0.01, SELL B_ONLY=0.01, SELL CORE_AB=0.02
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_gold_multi_strategy_guarded_demo_send_forever_aligned.py ^
  --out-dir "%OUT_DIR%" ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 20 ^
  --max-symbol-lot 1.0 ^
  --max-orders 1 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%
echo ============================================================
echo GOLD multi-strategy guarded demo-send weekly-log runner exit code: %EXITCODE%
echo Weekly log root: %LOG_ROOT%
echo Summary JSON: %OUT_DIR%\latest_gold_multi_strategy_guarded_demo_send_forever_aligned_result.json
echo Loop CSV: %OUT_DIR%\aligned_loop_log.csv
echo ============================================================
exit /b %EXITCODE%
