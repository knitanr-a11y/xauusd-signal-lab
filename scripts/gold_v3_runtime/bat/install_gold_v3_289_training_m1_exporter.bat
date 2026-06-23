@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\..\.."
set "SOURCE=%CD%\scripts\gold_v3_runtime\mt5\ExportGoldStage289TrainingM1.mq5"
set "FILES_DIR="
if defined GOLD_V3_MQL5_FILES set "FILES_DIR=%GOLD_V3_MQL5_FILES%"
if not defined FILES_DIR (
  for /d %%D in ("%APPDATA%\MetaQuotes\Terminal\*") do (
    if not defined FILES_DIR (
      set "CANDIDATE=%%~fD\MQL5\Files"
      if exist "!CANDIDATE!\goldsharp_m1.csv" set "FILES_DIR=!CANDIDATE!"
    )
  )
)
if not defined FILES_DIR (
  echo [BLOCKED] MT5 Files folder was not found.
  pause
  exit /b 2
)
if not exist "%SOURCE%" (
  echo [BLOCKED] Exporter source was not found: %SOURCE%
  pause
  exit /b 3
)
for %%I in ("%FILES_DIR%\..") do set "MQL5_DIR=%%~fI"
if not exist "%MQL5_DIR%\Scripts" mkdir "%MQL5_DIR%\Scripts"
copy /Y "%SOURCE%" "%MQL5_DIR%\Scripts\ExportGoldStage289TrainingM1.mq5" >nul
if errorlevel 1 (
  echo [BLOCKED] Could not copy the exporter.
  pause
  exit /b 4
)
echo.
echo Exporter installed:
echo %MQL5_DIR%\Scripts\ExportGoldStage289TrainingM1.mq5
echo.
echo This updated exporter writes historical GOLD M1, M5 and M15 files.
echo Next steps in MT5:
echo 1. Open MetaEditor and compile ExportGoldStage289TrainingM1.mq5 with F7.
echo 2. In MT5 Navigator, refresh Scripts.
echo 3. Run ExportGoldStage289TrainingM1 once on a GOLD chart.
echo 4. Wait for STAGE289_TRAINING_HISTORY_EXPORT_ALL_COMPLETE in the Experts log.
echo 5. Run run_gold_v3_292_safe_portfolio_live.bat again.
echo.
start "" explorer.exe "%MQL5_DIR%\Scripts"
pause
