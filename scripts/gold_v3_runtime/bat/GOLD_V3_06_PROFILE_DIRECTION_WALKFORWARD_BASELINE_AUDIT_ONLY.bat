@echo off
setlocal
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_06_profile_direction_walkforward_baseline_audit_only.py
endlocal
