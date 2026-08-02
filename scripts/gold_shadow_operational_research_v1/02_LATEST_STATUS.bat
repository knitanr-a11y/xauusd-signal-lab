@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CFG=%ROOT%\config\gold_shadow_operational_research_v1\local_config.json"
if not exist "%CFG%" (
  echo [BLOCKED] Run 01_COLLECT_SNAPSHOT.bat first.
  pause
  exit /b 2
)
where py >nul 2>&1 && (set "PY=py -3.12") || (set "PY=python")
pushd "%ROOT%"
%PY% -m scripts.gold_shadow_operational_research_v1.collect_operational_snapshot latest --config "%CFG%"
popd
pause
