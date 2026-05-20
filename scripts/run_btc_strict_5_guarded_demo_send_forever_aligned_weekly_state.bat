@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyy"') do set LOG_YEAR=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format MM"') do set LOG_MONTH=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=Get-Date; $c=[Globalization.CultureInfo]::InvariantCulture; $w=$c.Calendar.GetWeekOfYear($d,[Globalization.CalendarWeekRule]::FirstFourDayWeek,[DayOfWeek]::Monday); 'week_{0:D2}' -f $w"') do set LOG_WEEK=%%I

set LOG_ROOT=data\runtime_logs\btc\%LOG_YEAR%\%LOG_MONTH%\%LOG_WEEK%\strict_5_btc\guarded_demo_loop
set STATE_DIR=data\runtime_state\btc\strict_5
set SUMMARY_JSON=%LOG_ROOT%\latest_btc_strict_5_guarded_demo_send_forever_aligned_weekly_state_result.json
set SUMMARY_CSV=%LOG_ROOT%\aligned_loop_log.csv
set STOP_PREVIEW_TXT=%LOG_ROOT%\loop_stopped_discord_preview.txt
set STOP_PREVIEW_JSON=%LOG_ROOT%\loop_stopped_discord_preview.json

if not exist "%LOG_ROOT%" mkdir "%LOG_ROOT%"
if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"

echo ============================================================
echo BTC strict 5 GUARDED DEMO SEND FOREVER aligned runner
echo Weekly logs + persistent state ledger
echo LOG_ROOT=%LOG_ROOT%
echo STATE_DIR=%STATE_DIR%
echo Persistent order ledger: %STATE_DIR%\guarded_demo_order_ledger.csv
echo Sender --send requires BOTH --allow-demo-send and --send
echo Position policy: block_any / duplicate guard: order_key ledger
echo Lot: 0.01 / max-orders per cycle: 1
echo D1 is not used by BTC strict 5
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_btc_strict_5_guarded_demo_send_forever_aligned_weekly_state.py ^
  --log-base data\runtime_logs\btc ^
  --state-dir "%STATE_DIR%" ^
  --interval-minutes 15 ^
  --offset-seconds 5 ^
  --scan-recent-bars 5 ^
  --max-signal-age-minutes 30 ^
  --position-policy block_any ^
  --max-symbol-positions 1 ^
  --max-symbol-lot 0.01 ^
  --max-orders 1 ^
  --lot 0.01 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%

python scripts\notify_mochipoyo_loop_stopped.py ^
  --loop-name btc_strict_5_guarded_demo_send_forever_aligned_weekly_state ^
  --exit-code %EXITCODE% ^
  --summary-csv "%SUMMARY_CSV%" ^
  --preview-txt "%STOP_PREVIEW_TXT%" ^
  --preview-json "%STOP_PREVIEW_JSON%"

echo ============================================================
echo BTC strict 5 guarded demo-send weekly-state runner exit code: %EXITCODE%
echo Weekly log root: %LOG_ROOT%
echo Summary JSON: %SUMMARY_JSON%
echo Loop CSV: %SUMMARY_CSV%
echo Stop notification preview: %STOP_PREVIEW_TXT%
echo Persistent state dir: %STATE_DIR%
echo ============================================================
exit /b %EXITCODE%
