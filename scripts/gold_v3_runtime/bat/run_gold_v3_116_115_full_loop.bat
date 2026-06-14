@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 116/115 DEMO DISCORD ALERT-ONLY FULL LOOP
echo ============================================================
echo MODE: alert-only / no MT5 orders / NO_SIGNAL no Discord
echo Working directory:
echo   %CD%
echo ============================================================

set LOOP_COUNT=0

:main_loop
set /a LOOP_COUNT+=1
echo.
echo ------------------------------------------------------------
echo LOOP !LOOP_COUNT! START %DATE% %TIME%
echo ------------------------------------------------------------
echo [1/5] Stage116 exact ledger bridge
py -3 scripts\gold_v3_runtime\gold_v3_116_exact_ledger_bridge.py
if errorlevel 1 goto stop_branch

echo.
echo [2/5] Stage115D stale data watchdog --once
py -3 scripts\gold_v3_runtime\gold_v3_115d_stale_data_watchdog.py --once
if errorlevel 1 goto stop_branch

echo.
echo [3/5] Stage115C single BAT loop --once
py -3 scripts\gold_v3_runtime\gold_v3_115c_single_bat_loop.py --once --target-second 5 --retention-days 31
if errorlevel 1 goto stop_branch

echo.
echo [4/5] Waiting until next minute target-second 5
powershell -NoProfile -Command "$s=5; $n=Get-Date; $t=Get-Date -Hour $n.Hour -Minute $n.Minute -Second $s; if($t -le $n){$t=$t.AddMinutes(1)}; $wait=[int][Math]::Max(1,($t-$n).TotalSeconds); Write-Host ('Waiting seconds: ' + $wait); Start-Sleep -Seconds $wait"

echo.
echo [5/5] Loop completed, restarting
goto main_loop

:stop_branch
echo.
echo ============================================================
echo STOP_BRANCH: error detected in alert-only loop
echo [STOP 1/2] Queue BAT error notice
py -3 scripts\gold_v3_runtime\gold_v3_115x_bat_error_queue.py
echo [STOP 2/2] Send queued notice via Stage115B
py -3 scripts\gold_v3_runtime\gold_v3_115b_queue_sender.py
echo ============================================================
pause
exit /b 1
