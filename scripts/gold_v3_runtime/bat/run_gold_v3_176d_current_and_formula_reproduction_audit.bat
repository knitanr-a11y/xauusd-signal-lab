@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_176d_current_and_formula_reproduction_audit.py %*
if errorlevel 1 pause
endlocal
