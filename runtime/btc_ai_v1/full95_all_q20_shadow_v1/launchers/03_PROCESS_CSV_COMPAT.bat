@echo off
setlocal
title BTC AI V1 Full95 Q20 Shadow - ACTIVE OBSERVATION LOOP
cd /d "%~dp0.."

if not exist launchers\local_paths.bat (
  echo local_paths.bat was not found.
  echo This is the BTC AI V1 Full95 Q20 Shadow loop.
  pause
  exit /b 2
)

call launchers\local_paths.bat
"%PYTHON_EXE%" bootstrap\materialize_assets.py || (
  echo Frozen asset materialization failed. Full95 Q20 Shadow loop not started.
  pause
  exit /b 20
)

echo ============================================================
echo BTC AI V1 FULL95 ALL-Q20 SHADOW - ACTIVE OBSERVATION LOOP
echo Observation only / MT5 orders OFF / cycle interval 60 seconds
echo Close this window to stop ONLY the Full95 Q20 Shadow loop.
echo Stage55 runs separately and is not controlled by this window.
echo ============================================================

:loop
echo.
echo [%date% %time%] [BTC_FULL95_Q20_SHADOW] Starting observation cycle...
"%PYTHON_EXE%" bootstrap_run_shadow_csv_compat.py process --m1 "%M1_CSV%" --m15 "%M15_CSV%" --h1 "%H1_CSV%" --h4 "%H4_CSV%" --d1 "%D1_CSV%"
set "PROCESS_RC=%ERRORLEVEL%"
if not "%PROCESS_RC%"=="0" (
  echo.
  echo [%date% %time%] [BTC_FULL95_Q20_SHADOW] ERRORLEVEL=%PROCESS_RC%
  echo Full95 Q20 Shadow loop stopped for safety. It will not auto-retry after an error.
  pause
  exit /b %PROCESS_RC%
)
echo [%date% %time%] [BTC_FULL95_Q20_SHADOW] Cycle finished. Next cycle in 60 seconds.
timeout /t 60 /nobreak >nul
goto loop
