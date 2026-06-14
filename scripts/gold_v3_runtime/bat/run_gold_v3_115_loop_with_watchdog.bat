@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\..\..\.."

:loop
py -3 scripts\gold_v3_runtime\gold_v3_115d_stale_data_watchdog.py --once
if errorlevel 1 goto py_error

py -3 scripts\gold_v3_runtime\gold_v3_115c_single_bat_loop.py --once --target-second 5 --retention-days 31
if errorlevel 1 goto py_error

powershell -NoProfile -Command "$s=5; $n=Get-Date; $t=Get-Date -Hour $n.Hour -Minute $n.Minute -Second $s; if($t -le $n){$t=$t.AddMinutes(1)}; $wait=[int][Math]::Max(1,($t-$n).TotalSeconds); Start-Sleep -Seconds $wait"
goto loop

:py_error
py -3 scripts\gold_v3_runtime\gold_v3_115b_queue_sender.py
pause
exit /b 1
