@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c80_local_sync_from_25c79_audit_only.py

endlocal
