@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_176c_recovered_feature_candidate_replay_audit.py %*
if errorlevel 1 pause
endlocal
