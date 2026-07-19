@echo off
setlocal EnableExtensions

set "REPO_ROOT=%~dp0"
set "DATABASE=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3"
set "MT5_FILES_ROOT=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
set "MANIFEST=%REPO_ROOT%config\mochipoyo_alert_research\m7b_frozen_trigger_kernel_manifest_v1.json"
set "RUNNER=%REPO_ROOT%scripts\mochipoyo_alert_research\frozen_trigger_kernel_validation.py"
set "OUTPUT_DIR=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs"

echo ============================================================
echo Mochipoyo M7B Frozen Trigger Kernel Validation
echo AUDIT ONLY - Discord OFF - MT5 ORDER OFF - LIVE READY OFF
echo ============================================================
echo.

if "%LOCALAPPDATA%"=="" (
  echo [ERROR] LOCALAPPDATA is not defined.
  goto :FAILED
)

where py >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  echo Install or repair Python 3.12, then run this BAT again.
  goto :FAILED
)

py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 3.12 is not available through "py -3.12".
  goto :FAILED
)

if not exist "%DATABASE%" (
  echo [ERROR] SQLite database was not found:
  echo %DATABASE%
  goto :FAILED
)

if not exist "%MT5_FILES_ROOT%\" (
  echo [ERROR] MT5 Files root was not found:
  echo %MT5_FILES_ROOT%
  goto :FAILED
)

if not exist "%MANIFEST%" (
  echo [ERROR] Frozen manifest was not found:
  echo %MANIFEST%
  goto :FAILED
)

if not exist "%RUNNER%" (
  echo [ERROR] M7B runner was not found:
  echo %RUNNER%
  goto :FAILED
)

if not exist "%OUTPUT_DIR%\" mkdir "%OUTPUT_DIR%"
if errorlevel 1 (
  echo [ERROR] Could not create output directory:
  echo %OUTPUT_DIR%
  goto :FAILED
)

pushd "%REPO_ROOT%"
if errorlevel 1 (
  echo [ERROR] Could not change to repository root:
  echo %REPO_ROOT%
  goto :FAILED
)

echo [INFO] Repository : %REPO_ROOT%
echo [INFO] Database   : %DATABASE%
echo [INFO] MT5 Files  : %MT5_FILES_ROOT%
echo [INFO] Output     : %OUTPUT_DIR%
echo.
echo [INFO] Starting frozen M7B audit...
echo.

py -3.12 "%RUNNER%" ^
  --database "%DATABASE%" ^
  --mt5-files-root "%MT5_FILES_ROOT%" ^
  --manifest "%MANIFEST%" ^
  --output-dir "%OUTPUT_DIR%"

set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [FAILED] M7B audit stopped with exit code %EXIT_CODE%.
  echo No Discord notification or MT5 order was enabled.
  goto :FAILED
)

echo.
echo ============================================================
echo [SUCCESS] M7B audit completed.
echo Output files are in:
echo %OUTPUT_DIR%
echo ============================================================
echo.
pause
exit /b 0

:FAILED
echo.
echo The window will remain open so the error can be reviewed.
echo.
pause
exit /b 1
