@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c81_coreb_direct_sot_local_replay_audit_only.py

endlocal
