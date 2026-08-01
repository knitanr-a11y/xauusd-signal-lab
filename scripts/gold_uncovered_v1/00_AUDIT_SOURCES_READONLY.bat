@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_uncovered_v1_research"
set "REFERENCE=%ROOT%\config\gold_uncovered_v1\source_reference_20260802.json"
set "SCRIPT=%ROOT%\scripts\gold_uncovered_v1\source_audit.py"
set "OUT=%STATE%\latest_source_audit.json"

if not exist "%STATE%" mkdir "%STATE%"
if not exist "%REFERENCE%" (
  echo [BLOCKED] Source reference is missing:
  echo %REFERENCE%
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [BLOCKED] Source audit script is missing:
  echo %SCRIPT%
  pause
  exit /b 2
)

where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [BLOCKED] Python 3 was not found.
    pause
    exit /b 2
  )
  set "PY=python"
)

pushd "%ROOT%"
if errorlevel 1 (
  echo [BLOCKED] Could not enter repository root:
  echo %ROOT%
  pause
  exit /b 2
)

%PY% -m scripts.gold_uncovered_v1.source_audit --reference "%REFERENCE%" --output "%OUT%"
set "RC=%ERRORLEVEL%"
popd

echo.
echo [READ-ONLY] Audit output:
echo %OUT%
if exist "%OUT%" start "" notepad "%OUT%"
if not "%RC%"=="0" echo [BLOCKED] Phase 0 did not pass. Do not continue to features or outcomes.
pause
exit /b %RC%
