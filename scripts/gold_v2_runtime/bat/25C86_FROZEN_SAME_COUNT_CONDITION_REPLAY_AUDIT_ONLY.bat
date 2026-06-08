@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c86_frozen_same_count_condition_replay_audit_only.py

endlocal
