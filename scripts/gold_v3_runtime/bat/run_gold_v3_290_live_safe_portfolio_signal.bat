@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
if defined GOLD_V3_MQL5_FILES (set "FILES_DIR=%GOLD_V3_MQL5_FILES%") else (set "FILES_DIR=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\290_live_safe_portfolio"
set "PARITY_DIR=%OUT_DIR%\historical_parity"
set "LOCK_DIR=%OUT_DIR%\cycle.lock"
if not defined GOLD_V3_SAFE_PORTFOLIO_LEDGER exit /b 2
if not defined GOLD_V3_BASE_RESOLVED_HEALTH_LEDGER exit /b 2
if not defined GOLD_V3_PARITY_BASE_TRADES exit /b 2
if not defined GOLD_V3_PARITY_STAGE280_TRADES exit /b 2
if not defined GOLD_V3_PARITY_STAGE281_TRADES exit /b 2
if not defined GOLD_V3_PARITY_STRICT_TRADES exit /b 2
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
mkdir "%LOCK_DIR%" 2>nul
if errorlevel 1 exit /b 3
python "%RUNTIME%\gold_v3_290_historical_parity.py" --base "%GOLD_V3_PARITY_BASE_TRADES%" --stage280 "%GOLD_V3_PARITY_STAGE280_TRADES%" --stage281 "%GOLD_V3_PARITY_STAGE281_TRADES%" --strict "%GOLD_V3_PARITY_STRICT_TRADES%" --output "%PARITY_DIR%"
if errorlevel 1 (rmdir "%LOCK_DIR%"& exit /b 5)
python "%RUNTIME%\gold_v3_69_live_csv_condition_detector_audit.py" --candle-dir "%FILES_DIR%"
if errorlevel 1 (rmdir "%LOCK_DIR%"& exit /b 6)
python "%RUNTIME%\gold_v3_290_live_safe_portfolio.py" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%" --bootstrap-ledger "%GOLD_V3_SAFE_PORTFOLIO_LEDGER%" --base-resolved-health-ledger "%GOLD_V3_BASE_RESOLVED_HEALTH_LEDGER%" --exact-parity-report "%PARITY_DIR%\gold_v3_290_historical_parity.json" --authorization "USER_APPROVED_SAFE_PORTFOLIO_LIVE_SIGNAL_2026_06_23"
set "RC=%ERRORLEVEL%"
rmdir "%LOCK_DIR%" 2>nul
exit /b %RC%
