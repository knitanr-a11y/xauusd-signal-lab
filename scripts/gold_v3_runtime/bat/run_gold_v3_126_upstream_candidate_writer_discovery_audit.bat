@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo GOLD V3 126
py -3 scripts\gold_v3_runtime\gold_v3_126_upstream_candidate_writer_discovery_audit.py
if errorlevel 1 goto err

echo DONE. Check FX_OUTPUTS\gold_v3\126\paste_me.txt
pause
exit /b 0

:err
echo BLOCKED. Check FX_OUTPUTS\gold_v3\126\paste_me.txt
pause
exit /b 1
