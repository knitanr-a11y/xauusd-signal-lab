@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD specialist 8 AI review AUDIT ONLY V2 - NO API
echo - counts group/component/ledger rows
echo - checks whether all 8 expected strategy_ids exist in GROUP ledger
echo - no OpenAI API call
echo ============================================================

python scripts\gold_specialist_8\audit_gold_specialist_8_validation_targets.py

set EXIT_CODE=%ERRORLEVEL%
echo.
echo audit only v2 exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%
