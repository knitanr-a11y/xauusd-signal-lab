@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyy"') do set LOG_YEAR=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format MM"') do set LOG_MONTH=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=Get-Date; $c=[Globalization.CultureInfo]::InvariantCulture; $w=$c.Calendar.GetWeekOfYear($d,[Globalization.CalendarWeekRule]::FirstFourDayWeek,[DayOfWeek]::Monday); 'week_{0:D2}' -f $w"') do set LOG_WEEK=%%I

set LOG_ROOT=data\runtime_logs\gold\%LOG_YEAR%\%LOG_MONTH%\%LOG_WEEK%\multi_strategy_gold\loop
set STATE_DIR=data\runtime_state\gold\multi_strategy
set SUMMARY_JSON=%LOG_ROOT%\latest_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_result.json
set SUMMARY_CSV=%LOG_ROOT%\aligned_loop_log.csv
set STOP_PREVIEW_TXT=%LOG_ROOT%\loop_stopped_discord_preview.txt
set STOP_PREVIEW_JSON=%LOG_ROOT%\loop_stopped_discord_preview.json

if not exist "%LOG_ROOT%" mkdir "%LOG_ROOT%"
if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"

echo ============================================================
echo GOLD multi-strategy GUARDED DEMO SEND FOREVER aligned runner
echo Weekly logs + persistent state ledger
echo Existing Mochipoyo GOLD BAT/state is not modified
echo LOG_ROOT=%LOG_ROOT%
echo STATE_DIR=%STATE_DIR%
echo Persistent order ledger: %STATE_DIR%\guarded_demo_order_ledger.csv
echo Sender --send requires BOTH --allow-demo-send and --send
echo Position policy: allow_any_until_max / duplicate guard: order_key ledger
echo Adapter lot: BUY=0.01, SELL B_ONLY=0.01, SELL CORE_AB=0.02
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.py ^
  --log-base data\runtime_logs\gold ^
  --state-dir "%STATE_DIR%" ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 20 ^
  --max-symbol-lot 1.0 ^
  --max-orders 1 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%

python scripts\notify_mochipoyo_loop_stopped.py ^
  --loop-name gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state ^
  --exit-code %EXITCODE% ^
  --summary-csv "%SUMMARY_CSV%" ^
  --preview-txt "%STOP_PREVIEW_TXT%" ^
  --preview-json "%STOP_PREVIEW_JSON%"

echo ============================================================
echo GOLD multi-strategy guarded demo-send weekly-state runner exit code: %EXITCODE%
echo Weekly log root: %LOG_ROOT%
echo Summary JSON: %SUMMARY_JSON%
echo Loop CSV: %SUMMARY_CSV%
echo Stop notification preview: %STOP_PREVIEW_TXT%
echo Persistent state dir: %STATE_DIR%
echo ============================================================
exit /b %EXITCODE%
