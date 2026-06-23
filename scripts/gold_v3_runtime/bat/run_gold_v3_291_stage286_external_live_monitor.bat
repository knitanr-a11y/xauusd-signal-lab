@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
set "FILES_DIR="

rem Use an explicitly configured Files folder when one exists.
if defined GOLD_V3_MQL5_FILES set "FILES_DIR=%GOLD_V3_MQL5_FILES%"

rem Otherwise find the MT5 terminal whose Files folder contains all required CSVs.
if not defined FILES_DIR (
  for /d %%D in ("%APPDATA%\MetaQuotes\Terminal\*") do (
    if not defined FILES_DIR (
      set "CANDIDATE=%%~fD\MQL5\Files"
      if exist "!CANDIDATE!\goldsharp_m1.csv" if exist "!CANDIDATE!\goldsharp_m5.csv" if exist "!CANDIDATE!\goldsharp_m15.csv" if exist "!CANDIDATE!\goldsharp_h1.csv" if exist "!CANDIDATE!\goldsharp_h4.csv" if exist "!CANDIDATE!\goldsharp_d1.csv" if exist "!CANDIDATE!\us500cashsharp_m15.csv" if exist "!CANDIDATE!\us100cashsharp_m15.csv" set "FILES_DIR=!CANDIDATE!"
    )
  )
)

if not defined FILES_DIR (
  echo.
  echo [BLOCKED] Required MT5 CSV files were not found automatically.
  echo Confirm that the candle export EA is running and the following files exist:
  echo   goldsharp_m1.csv / m5 / m15 / h1 / h4 / d1
  echo   us500cashsharp_m15.csv
  echo   us100cashsharp_m15.csv
  echo.
  pause
  exit /b 2
)

set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\291_stage286_external_live_m15"
echo [INFO] MT5 Files: %FILES_DIR%
echo [INFO] Output   : %OUT_DIR%

rem Find Python.
where python >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>&1
  if errorlevel 1 (
    echo [BLOCKED] Python was not found.
    pause
    exit /b 3
  )
  set "PYTHON_CMD=py -3"
)

rem Install only the packages needed by the current runtime when missing.
%PYTHON_CMD% -c "import numpy, pandas, lightgbm" >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing required Python packages: numpy pandas lightgbm
  %PYTHON_CMD% -m pip install numpy pandas lightgbm
  if errorlevel 1 (
    echo [BLOCKED] Python package installation failed.
    pause
    exit /b 4
  )
)

%PYTHON_CMD% "%RUNTIME%\gold_v3_291_stage286_external_live_monitor.py" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%" --lookback-hours 96
set "RC=%ERRORLEVEL%"

echo.
if exist "%OUT_DIR%\gold_v3_291_summary.json" (
  echo ===== Stage291 summary =====
  type "%OUT_DIR%\gold_v3_291_summary.json"
) else (
  echo [BLOCKED] Summary file was not created.
)
echo.
echo Output folder:
echo %OUT_DIR%
echo.
pause
exit /b %RC%
