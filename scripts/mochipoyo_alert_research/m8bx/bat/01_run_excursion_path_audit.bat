@echo off
setlocal
set "SCRIPT=%~dp0..\python\run_excursion_path_audit.py"

python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8BX excursion path audit was blocked.
  echo Keep M8C running. Do not reset M7C or M8C.
  pause
  exit /b %RC%
)
echo [OK] M8BX complete. Run 02_open_latest_results.bat and upload 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
