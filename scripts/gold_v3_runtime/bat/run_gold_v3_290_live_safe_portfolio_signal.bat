@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
if defined GOLD_V3_MQL5_FILES (set "FILES_DIR=%GOLD_V3_MQL5_FILES%") else (set "FILES_DIR=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\290_live_safe_portfolio"
set "LOCK_DIR=%OUT_DIR%\cycle.lock"
if not defined GOLD_V3_SAFE_PORTFOLIO_LEDGER (echo [BLOCKED] GOLD_V3_SAFE_PORTFOLIO_LEDGER is required.& exit /b 2)
if not defined GOLD_V3_BASE_RESOLVED_HEALTH_LEDGER (echo [BLOCKED] GOLD_V3_BASE_RESOLVED_HEALTH_LEDGER is required.& exit /b 2)
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
mkdir "%LOCK_DIR%" 2>nul
if errorlevel 1 (echo [BLOCKED] Another cycle is running.& exit /b 3)
for %%F in (goldsharp_m1.csv goldsharp_m5.csv goldsharp_m15.csv goldsharp_h1.csv goldsharp_h4.csv goldsharp_d1.csv us500cashsharp_m15.csv us100cashsharp_m15.csv) do if not exist "%FILES_DIR%\%%F" (echo [BLOCKED] Missing %%F& rmdir "%LOCK_DIR%"& exit /b 4)
python "%RUNTIME%\gold_v3_69_live_csv_condition_detector_audit.py" --candle-dir "%FILES_DIR%"
if errorlevel 1 (rmdir "%LOCK_DIR%"& exit /b 5)
python "%RUNTIME%\gold_v3_290_live_safe_portfolio.py" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%" --bootstrap-ledger "%GOLD_V3_SAFE_PORTFOLIO_LEDGER%" --base-resolved-health-ledger "%GOLD_V3_BASE_RESOLVED_HEALTH_LEDGER%" --bootstrap-state-start "2026-01-01 00:00:00" --authorization "USER_APPROVED_SAFE_PORTFOLIO_LIVE_SIGNAL_2026_06_23"
set "RC=%ERRORLEVEL%"
rmdir "%LOCK_DIR%" 2>nul
if exist "%OUT_DIR%\gold_v3_290_summary.json" type "%OUT_DIR%\gold_v3_290_summary.json"
exit /b %RC%
