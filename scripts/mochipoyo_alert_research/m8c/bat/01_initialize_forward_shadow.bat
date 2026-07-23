@echo off
setlocal
set "SCRIPT=%~dp0..\python\initialize_forward_shadow.py"
python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8C initialization was blocked.
  echo Do not reset M7C or M8C manifests manually.
  pause
  exit /b %RC%
)
echo [OK] 01 complete. Next run 02_run_forward_shadow_forever.bat.
pause
exit /b 0
