@echo off
setlocal
set "SCRIPT=%~dp0..\python\run_pullback_state_feature_audit.py"
python "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8BZ pullback-state feature audit was blocked.
  echo Keep M8C, M7C, and collector unchanged. Do not reset any prospective start.
  pause
  exit /b %RC%
)
echo [OK] M8BZ complete. Run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
