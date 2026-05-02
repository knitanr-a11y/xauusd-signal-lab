@echo off
setlocal
cd /d "%~dp0.."
echo Running XM KIWAMI data verification...
echo.
py scripts\verify_xm_kiwami_data.py
if errorlevel 1 (
  echo.
  echo Verification failed.
  echo If Python is not found, install Python or try: python scripts\verify_xm_kiwami_data.py
) else (
  echo.
  echo Verification succeeded.
)
echo.
pause
