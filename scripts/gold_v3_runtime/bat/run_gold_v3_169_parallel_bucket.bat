@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_169_parallel_bucket_cap_audit.py
pause
