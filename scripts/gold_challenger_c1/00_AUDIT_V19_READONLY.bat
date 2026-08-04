@echo off
setlocal EnableExtensions
title GOLD Challenger C1 Shadow - V19 Read-Only Audit
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "PY=%STATE%\venv\Scripts\python.exe"
set "OUT=%STATE%\challenger_v19_readonly_audit.txt"
echo ============================================================
echo GOLD CHALLENGER C1 SHADOW - V19 READ-ONLY AUDIT
echo V19 is read-only / No runtime state reset / MT5 orders OFF
echo ============================================================

if not exist "%STATE%" mkdir "%STATE%"
if not exist "%PY%" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Run 01_INSTALL_SHADOW.bat first.
  pause
  exit /b 2
)
if not exist "%CONFIG%" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Challenger local_config.json is missing:
  echo %CONFIG%
  pause
  exit /b 2
)
if not exist "%ROOT%\scripts\gold_challenger_c1\audit_v19_runtime.py" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Audit module is missing from this checkout.
  echo ROOT=%ROOT%
  echo Fetch origin and Pull origin on feature/gold-v19-challenger-c1-audit.
  pause
  exit /b 2
)

pushd "%ROOT%"
if errorlevel 1 (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Could not enter repository root:
  echo %ROOT%
  pause
  exit /b 2
)
"%PY%" -m scripts.gold_challenger_c1.audit_v19_runtime --config "%CONFIG%" > "%OUT%" 2>&1
set "RC=%ERRORLEVEL%"
popd

echo [GOLD_CHALLENGER_C1_SHADOW] [READ-ONLY] Audit written to:
echo %OUT%
if exist "%OUT%" (
  start "" notepad "%OUT%"
) else (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Audit output was not created.
  pause
  exit /b 2
)
pause
exit /b %RC%
