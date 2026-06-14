@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\..\..\.."

:main_loop
py -3 scripts\gold_v3_runtime\gold_v3_116_exact_ledger_bridge.py
if errorlevel 1 goto stop_branch

py -3 scripts\gold_v3_runtime\gold_v3_115d_stale_data_watchdog.py --once
if errorlevel 1 goto stop_branch

py -3 scripts\gold_v3_runtime\gold_v3_115c_single_bat_loop.py --once --target-second 5 --retention-days 31
if errorlevel 1 goto stop_branch

powershell -NoProfile -Command "$s=5; $n=Get-Date; $t=Get-Date -Hour $n.Hour -Minute $n.Minute -Second $s; if($t -le $n){$t=$t.AddMinutes(1)}; $wait=[int][Math]::Max(1,($t-$n).TotalSeconds); Start-Sleep -Seconds $wait"
goto main_loop

:stop_branch
py -3 scripts\gold_v3_runtime\gold_v3_115x_bat_error_queue.py
py -3 scripts\gold_v3_runtime\gold_v3_115b_queue_sender.py
pause
exit /b 1
