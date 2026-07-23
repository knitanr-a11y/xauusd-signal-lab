@echo off
setlocal
set "SCRIPT=%~dp0..\python\run_multitimeframe_rci_context_audit.py"
python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8BZ2 multi-timeframe RCI context audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  pause
  exit /b %RC%
)
echo [OK] 01 complete. Run 02_open_latest_results.bat and upload 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
