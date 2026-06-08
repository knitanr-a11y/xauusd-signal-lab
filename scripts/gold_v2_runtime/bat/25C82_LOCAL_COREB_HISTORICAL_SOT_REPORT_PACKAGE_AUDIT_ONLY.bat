@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c82_local_coreb_historical_sot_report_package_audit_only.py

endlocal
