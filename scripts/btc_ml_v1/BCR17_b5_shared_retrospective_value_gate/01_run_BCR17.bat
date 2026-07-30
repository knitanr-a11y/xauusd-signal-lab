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

set "PY_SCRIPT=scripts\btc_ml_v1\BCR17_b5_shared_retrospective_value_gate\python\run_bcr17_b5_shared_value_gate.py"
set "CONTRACT=configs\btc_ml_v1\btc_bcr17_b5_shared_retrospective_value_gate_contract_20260731.json"
set "DEFAULT_INPUT=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv"
set "BCR16_PACKAGE=%LOCAL_ROOT%\btc_ml_v1\outputs\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\LATEST\BCR16_B5_OUTCOME_BLIND_CAPABILITY_AUDIT_20260731.zip"
set "OUTPUT_ROOT=%LOCAL_ROOT%\btc_ml_v1\outputs\BCR17_b5_shared_retrospective_value_gate"
set "OUTPUT_DIR=%OUTPUT_ROOT%\LATEST"
set "CORE_ZIP=%OUTPUT_DIR%\BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_20260731.zip"
set "REPEAT_JSON=%OUTPUT_DIR%\deterministic_repeat.json"
set "PACKAGE_SHA=%OUTPUT_DIR%\package_sha256.txt"
set "UPLOAD_ZIP=%OUTPUT_DIR%\99_UPLOAD_PACKAGE.zip"

if defined BTC_BCR17_INPUT (
  set "INPUT=%BTC_BCR17_INPUT%"
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
  echo [BCR17] FAILED: Python was not found.
  pause
  exit /b 9009
)

if not exist "%PY_SCRIPT%" (
  echo [BCR17] FAILED: Python script was not found.
  echo %PY_SCRIPT%
  pause
  exit /b 2
)
if not exist "%CONTRACT%" (
  echo [BCR17] FAILED: Contract was not found.
  echo %CONTRACT%
  pause
  exit /b 2
)
if not exist "%INPUT%" (
  echo [BCR17] FAILED: BTC M15 input was not found.
  echo %INPUT%
  echo No fallback or alternative CSV was used.
  pause
  exit /b 2
)
if not exist "%BCR16_PACKAGE%" (
  echo [BCR17] FAILED: Accepted BCR16 inner package was not found.
  echo %BCR16_PACKAGE%
  echo Pull and run BCR16 only if the accepted package was removed. Do not substitute another ledger.
  pause
  exit /b 2
)

where powershell >nul 2>&1
if errorlevel 1 (
  echo [BCR17] FAILED: Windows PowerShell was not found.
  pause
  exit /b 9009
)

echo ============================================================
echo BCR17 - B5 SHARED RETROSPECTIVE VALUE GATE
echo ============================================================
echo Python          : %PYTHON_CMD%
echo BTC M15 input   : %INPUT%
echo BCR16 package   : %BCR16_PACKAGE%
echo Output root     : %OUTPUT_ROOT%
echo Upload package  : %UPLOAD_ZIP%
echo Costs           : C0 observed spread; C2 +25%% spread each fill
echo Commission      : 0
echo Swap            : NOT INCLUDED; rollover rows PRE_SWAP_ONLY
echo Machines        : ALL EIGHT, BOTH DIRECTIONS, NO RESCUE
echo Collector/M7C   : KEEP RUNNING, NO CHANGE
echo GOLD/MOCHIPOYO  : NO CHANGE
echo Discord/MT5     : OFF
echo ============================================================
echo.

%PYTHON_CMD% "%PY_SCRIPT%" ^
  --input "%INPUT%" ^
  --bcr16-package "%BCR16_PACKAGE%" ^
  --contract "%CONTRACT%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --allow-prefix-rehydrate ^
  --repeat-check
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [BCR17] FAILED: value-gate execution returned exit_code=%EXIT_CODE%.
  echo [BCR17] No fallback, alternate input, machine deletion or side deletion was used.
  if exist "%OUTPUT_DIR%" start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b %EXIT_CODE%
)

if not exist "%CORE_ZIP%" (
  echo [BCR17] FAILED: core deterministic ZIP was not created.
  if exist "%OUTPUT_DIR%" start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)
if not exist "%REPEAT_JSON%" (
  echo [BCR17] FAILED: deterministic_repeat.json was not created.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)
if not exist "%PACKAGE_SHA%" (
  echo [BCR17] FAILED: package_sha256.txt was not created.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)

if exist "%UPLOAD_ZIP%" del /q "%UPLOAD_ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Compress-Archive -LiteralPath @('%CORE_ZIP%','%REPEAT_JSON%','%PACKAGE_SHA%') -DestinationPath '%UPLOAD_ZIP%' -CompressionLevel Optimal -Force"
set "ZIP_EXIT=%ERRORLEVEL%"
if not "%ZIP_EXIT%"=="0" (
  echo [BCR17] FAILED: 99_UPLOAD_PACKAGE.zip could not be created.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b %ZIP_EXIT%
)

if exist "%UPLOAD_ZIP%" (
  start "" explorer.exe /select,"%UPLOAD_ZIP%"
) else (
  echo [BCR17] FAILED: upload ZIP is missing after packaging.
  start "" explorer.exe "%OUTPUT_DIR%"
  pause
  exit /b 3
)

echo.
echo [BCR17] COMPLETED.
echo [BCR17] Upload only the selected file:
echo %UPLOAD_ZIP%
echo.
pause
exit /b 0
