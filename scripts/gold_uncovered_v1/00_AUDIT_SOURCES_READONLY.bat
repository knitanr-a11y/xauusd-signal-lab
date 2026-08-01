@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_uncovered_v1_research"
set "REFERENCE=%ROOT%\config\gold_uncovered_v1\source_reference_20260802.json"
set "SCRIPT=%ROOT%\scripts\gold_uncovered_v1\source_audit.py"
set "RUNNER=%ROOT%\scripts\gold_uncovered_v1\source_audit_runner.py"
set "SELFTEST=%ROOT%\scripts\gold_uncovered_v1\self_test.py"
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
if not exist "%RUNNER%" (
  echo [BLOCKED] Source audit runner is missing:
  echo %RUNNER%
  pause
  exit /b 2
)
if not exist "%SELFTEST%" (
  echo [BLOCKED] Source audit self-test is missing:
  echo %SELFTEST%
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

%PY% -m compileall -q scripts\gold_uncovered_v1
if errorlevel 1 (
  popd
  echo [BLOCKED] GU1 Python compilation failed.
  pause
  exit /b 2
)
%PY% -m scripts.gold_uncovered_v1.self_test
if errorlevel 1 (
  popd
  echo [BLOCKED] GU1 source audit self-test failed.
  pause
  exit /b 2
)
%PY% -m scripts.gold_uncovered_v1.source_audit_runner --reference "%REFERENCE%" --output "%OUT%"
set "RC=%ERRORLEVEL%"
popd

echo.
echo [READ-ONLY] Audit output:
echo %OUT%
if exist "%OUT%" start "" notepad "%OUT%"
if not "%RC%"=="0" echo [BLOCKED] Phase 0 did not pass. Do not continue to features or outcomes.
pause
exit /b %RC%
