@echo off
setlocal
set "SCRIPT=%~dp0..\python\run_forward_shadow_forever.py"
python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8C forward shadow stopped with exit code %RC%.
  echo Do not reinitialize automatically. Send the displayed error to ChatGPT.
  pause
  exit /b %RC%
)
pause
exit /b 0
