@echo off
setlocal
set "ROOT=%~dp0"
set "TARGET=%ROOT%scripts\gold_ml_v1\live_research_challenger\run_live_autotrade_loop.bat"
if not exist "%TARGET%" (
  echo ERROR: autotrade loop BAT was not found.
  echo "%TARGET%"
  pause
  exit /b 2
)
call "%TARGET%"
exit /b %ERRORLEVEL%
