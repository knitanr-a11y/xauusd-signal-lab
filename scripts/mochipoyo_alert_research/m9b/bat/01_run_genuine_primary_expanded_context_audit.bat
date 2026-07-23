@echo off
setlocal
set "SCRIPT=%~dp0..\python\run_genuine_primary_expanded_context_audit.py"

if not exist "%SCRIPT%" (
  echo [M9B BLOCKED] Python audit script is missing: %SCRIPT%
  pause
  exit /b 2
)

python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M9B genuine-primary expanded context audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  pause
  exit /b %RC%
)

echo [OK] M9B complete. Run 02_open_latest_results.bat and upload 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
