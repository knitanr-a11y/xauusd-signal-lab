@echo off
setlocal
cd /d "%~dp0\..\..\..\.."
py -3.12 scripts\gold_ml_v1\research_challenger\verify_final_research_challenger.py
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Final research challenger parity FAILED. Exit code: %EXIT_CODE%
  exit /b %EXIT_CODE%
)
echo.
echo Final research challenger parity PASSED.
exit /b 0
