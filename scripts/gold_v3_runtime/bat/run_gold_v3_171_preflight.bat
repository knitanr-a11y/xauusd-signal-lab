@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_171_parallel_contract_preflight_audit.py
pause
