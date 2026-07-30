@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab"
)

set "PY_SCRIPT=scripts\btc_ml_v1\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\python\run_bcr16_b5_capability_audit.py"
set "CONTRACT=configs\btc_ml_v1\btc_bcr15_causal_h1_impulse_m15_pullback_reclaim_design_contract_20260731.json"
set "DEFAULT_INPUT=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv"
set "OUTPUT_ROOT=%LOCAL_ROOT%\btc_ml_v1\outputs\BCR16_b5_h1_impulse_m15_reclaim_capability_audit"
set "OUTPUT_DIR=%OUTPUT_ROOT%\LATEST"
set "CORE_ZIP=%OUTPUT_DIR%\BCR16_B5_OUTCOME_BLIND_CAPABILITY_AUDIT_20260731.zip"
set "REPEAT_JSON=%OUTPUT_DIR%\deterministic_repeat.json"
set "PACKAGE_SHA=%OUTPUT_DIR%\package_sha256.txt"
set "UPLOAD_ZIP=%OUTPUT_DIR%\99_UPLOAD_PACKAGE.zip"

if defined BTC_BCR16_INPUT (
  set "INPUT=%BTC_BCR16_INPUT%"
) else (
  set "INPUT=%DEFAULT_INPUT%"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [BCR16] FAILED: Python was not found.
  pause
  exit /b 9009
)

if not exist "%PY_SCRIPT%" (
  echo [BCR16] FAILED: Python script was not found.
  echo %PY_SCRIPT%
  pause
  exit /b 2
)
if not exist "%CONTRACT%" (
  echo [BCR16] FAILED: BCR15 contract was not found.
  echo %CONTRACT%
  pause
  exit /b 2
)
if not exist "%INPUT%" (
  echo [BCR16] FAILED: BTC M15 input was not found.
  echo %INPUT%
  echo No fallback or alternative CSV was used.
  pause
  exit /b 2
)

where powershell >nul 2>&1
if errorlevel 1 (
  echo [BCR16] FAILED: Windows PowerShell was not found.
  echo The upload ZIP could not be created.
  pause
  exit /b 9009
)

echo ============================================================
echo BCR16 - B5 H1 IMPULSE / M15 RECLAIM CAPABILITY AUDIT
echo ============================================================
echo Python          : %PYTHON_CMD%
echo BTC M15 input   : %INPUT%
echo Output root     : %OUTPUT_ROOT%
echo Upload package  : %UPLOAD_ZIP%
echo Outcome fields  : NOT READ OR EXPORTED
echo Fallback        : FORBIDDEN
echo Collector/M7C   : KEEP RUNNING, NO CHANGE
echo GOLD/MOCHIPOYO  : NO CHANGE
echo Discord/MT5     : OFF
echo ============================================================
echo.

%PYTHON_CMD% "%PY_SCRIPT%" ^
  --input "%INPUT%" ^
  --contract "%CONTRACT%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --allow-prefix-rehydrate ^
  --repeat-check
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [BCR16] FAILED: audit execution returned exit_code=%EXIT_CODE%.
  echo [BCR16] No fallback or alternative input was used.
  if exist "%OUTPUT_DIR%" start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b %EXIT_CODE%
)

if not exist "%CORE_ZIP%" (
  echo [BCR16] FAILED: core deterministic ZIP was not created.
  if exist "%OUTPUT_DIR%" start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)
if not exist "%REPEAT_JSON%" (
  echo [BCR16] FAILED: deterministic_repeat.json was not created.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)
if not exist "%PACKAGE_SHA%" (
  echo [BCR16] FAILED: package_sha256.txt was not created.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)

if exist "%UPLOAD_ZIP%" del /q "%UPLOAD_ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Compress-Archive -LiteralPath @('%CORE_ZIP%','%REPEAT_JSON%','%PACKAGE_SHA%') -DestinationPath '%UPLOAD_ZIP%' -CompressionLevel Optimal -Force"
set "ZIP_EXIT=%ERRORLEVEL%"
if not "%ZIP_EXIT%"=="0" (
  echo [BCR16] FAILED: 99_UPLOAD_PACKAGE.zip could not be created.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b %ZIP_EXIT%
)

if exist "%UPLOAD_ZIP%" (
  start "" explorer.exe /select,"%UPLOAD_ZIP%"
) else (
  echo [BCR16] FAILED: upload ZIP is missing after packaging.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)

echo.
echo [BCR16] COMPLETED.
echo [BCR16] Upload only the selected file:
echo %UPLOAD_ZIP%
echo.
pause
exit /b 0
