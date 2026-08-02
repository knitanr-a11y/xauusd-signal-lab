@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CFG=%ROOT%\config\gold_shadow_operational_research_v1\local_config.json"
if not exist "%CFG%" (
  copy /Y "%ROOT%\config\gold_shadow_operational_research_v1\local_config.example.json" "%CFG%" >nul
  echo Created %CFG%
  echo Review the three state_root paths, save, and run this BAT again.
  notepad "%CFG%"
  pause
  exit /b 2
)
where py >nul 2>&1 && (set "PY=py -3.12") || (set "PY=python")
pushd "%ROOT%"
%PY% -m scripts.gold_shadow_operational_research_v1.collect_operational_snapshot collect --config "%CFG%"
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" goto :error
echo.
echo [OK] Read-only operational snapshot created.
pause
exit /b 0
:error
echo.
echo [BLOCKED] Snapshot collection failed.
pause
exit /b 2
