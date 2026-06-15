@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo GOLD V3 123 107K2 WRITER DISCOVERY AUDIT
py -3 scripts\gold_v3_runtime\gold_v3_123_107k2_writer_discovery_audit.py
if errorlevel 1 goto err

echo DONE. Check FX_OUTPUTS\gold_v3\123\paste_me.txt
pause
exit /b 0

:err
echo FAILED. Check FX_OUTPUTS\gold_v3\123\paste_me.txt
pause
exit /b 1
