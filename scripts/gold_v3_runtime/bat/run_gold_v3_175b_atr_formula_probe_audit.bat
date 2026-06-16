@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_175b_atr_formula_probe_audit.py %*
if errorlevel 1 pause
endlocal
