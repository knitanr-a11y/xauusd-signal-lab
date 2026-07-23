@echo off
setlocal
set "SCRIPT=%~dp0..\python\run_pullback_entry_opportunity_audit.py"
python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8BY pullback-entry opportunity audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  pause
  exit /b %RC%
)
echo [OK] M8BY complete. Run 02_open_latest_results.bat and upload 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
