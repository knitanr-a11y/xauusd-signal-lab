@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
if defined GOLD_V3_MQL5_FILES (
  set "FILES_DIR=%GOLD_V3_MQL5_FILES%"
) else (
  set "FILES_DIR=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
)
set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\291_stage286_external_live_m15"
for %%F in (goldsharp_m1.csv goldsharp_m5.csv goldsharp_m15.csv goldsharp_h1.csv goldsharp_h4.csv goldsharp_d1.csv us500cashsharp_m15.csv us100cashsharp_m15.csv) do (
  if not exist "%FILES_DIR%\%%F" (
    echo [BLOCKED] Missing "%FILES_DIR%\%%F"
    exit /b 2
  )
)
python "%RUNTIME%\gold_v3_291_stage286_external_live_monitor.py" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%" --lookback-hours 96
set "RC=%ERRORLEVEL%"
if exist "%OUT_DIR%\gold_v3_291_summary.json" type "%OUT_DIR%\gold_v3_291_summary.json"
exit /b %RC%
