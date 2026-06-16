@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_176b_historical_feature_definition_recovery_audit.py %*
if errorlevel 1 pause
endlocal
